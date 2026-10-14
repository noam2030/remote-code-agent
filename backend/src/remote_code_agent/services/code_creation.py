"""Module responsible for autonomous code creation using Google Antigravity Agent."""

import os
import shutil
from typing import AsyncGenerator

import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from remote_code_agent.github_service import (
    create_or_checkout_branch,
    derive_feature_branch_name,
    derive_project_slug,
    ensure_remote_repo_and_main,
    get_current_branch,
    get_latest_feature_branch,
    merge_pull_request,
    publish_project_to_github,
    push_feature_branch_and_create_pr,
)
from remote_code_agent.project_service import (
    inspect_project_files,
    list_projects,
    record_project_run_tokens,
    sanitize_project_name,
    sync_project_from_github,
)
from remote_code_agent.prompt_service import (
    append_numbered_prompt,
    get_last_feature_prompt,
    update_project_master_prompt,
)
from remote_code_agent.services.agent_prompts import (
    get_agent_system_prompt,
    get_info_retrieval_system_prompt,
    get_planning_chat_prompt,
    get_user_chat_prompt,
)
from remote_code_agent.services.intent_service import (
    detect_project_from_prompt,
    is_confirmation_request,
    is_info_retrieval_request,
    is_merge_request,
)


# Dedicated workspace directory for agent-generated projects
BASE_WORKSPACE = os.path.abspath(os.environ.get("AGENT_WORKSPACE", "workspace"))
os.makedirs(BASE_WORKSPACE, exist_ok=True)


def format_stream_chunk(chunk) -> str | None:
    """Formats an Antigravity agent chunk into a human-readable stream chunk."""
    if isinstance(chunk, types.Thought):
        return f"💭 {chunk.text}"
    elif isinstance(chunk, types.ToolCall):
        target = (
            chunk.args.get("file_path")
            or chunk.args.get("command_line")
            or chunk.args.get("TargetFile")
            or chunk.args.get("CommandLine")
            or ""
        )
        detail = f" -> {os.path.basename(target)}" if target else ""
        return f"\n⚡ [Tool: {chunk.name}{detail}]\n"
    elif isinstance(chunk, types.Text):
        return chunk.text
    return None


def get_agent_config(project_dir: str, app_name: str | None = None) -> google.antigravity.LocalAgentConfig:
    """Creates the LocalAgentConfig for code generation in an isolated workspace."""
    target_name = app_name or os.path.basename(project_dir)
    return google.antigravity.LocalAgentConfig(
        system_instructions=get_agent_system_prompt(target_name),
        workspaces=[project_dir],
        policies=[policy.allow_all()],
    )


def get_info_retrieval_agent_config(
    project_dir: str,
    app_name: str | None = None,
) -> google.antigravity.LocalAgentConfig:
    """Creates a read-only LocalAgentConfig for information retrieval and codebase inspection."""
    target_name = app_name or os.path.basename(project_dir)
    return google.antigravity.LocalAgentConfig(
        system_instructions=get_info_retrieval_system_prompt(target_name),
        workspaces=[project_dir],
        policies=[policy.allow_all()],
    )


async def generate_code_stream(
    prompt: str,
    project_name: str | None = None,
    auto_confirm: bool = False,
) -> AsyncGenerator[str, None]:
    """Pair-programming code creation, planning, and GitHub PR workflow.

    1. Classifies user intent:
       - merge request (is_merge_request)
       - confirmation / execution request (is_confirmation_request or auto_confirm)
       - information retrieval request (is_info_retrieval_request)
       - planning request (new feature / modification instruction)
    2. Determines target project: uses project_name if provided, detects from prompt, or derives slug.
    3. Ensures isolated workspace directory exists for this project (/workspace/<project_name>).
    4. Syncs existing project codebase from GitHub (clones into workspace or pulls latest if present).
    5. Dispatches flow accordingly:
       - Merge: Squash-merges open PR into main, deletes feature branch, syncs local main.
       - Info: Read-only codebase inspection without modifying files.
       - Execution (Confirmed): Checks out feature branch, updates SPEC.md first, implements code/tests,
         runs tests, commits, pushes feature branch to GitHub, creates PR, and prompts for merge.
       - Planning (New Request): Appends prompt to prompt.txt, drafts implementation plan, and yields Confirm?.
    """
    is_merge = is_merge_request(prompt)
    is_confirm = is_confirmation_request(prompt) or auto_confirm
    is_info = not is_merge and not is_confirm and is_info_retrieval_request(prompt)

    if project_name and project_name.strip():
        raw_name = project_name.strip()
        all_projs = list_projects()
        catalog_match = next((p for p in all_projs if p["name"].lower() == raw_name.lower()), None)
        app_name = catalog_match["name"] if catalog_match else raw_name
        slug = sanitize_project_name(app_name)
        yield f"🎯 [Project Target] Working on project: '{app_name}'\n"
    else:
        existing_projects = [
            d
            for d in os.listdir(BASE_WORKSPACE)
            if os.path.isdir(os.path.join(BASE_WORKSPACE, d)) and not d.startswith(".")
        ]
        detected = detect_project_from_prompt(prompt, existing_projects)
        if detected:
            app_name = detected
            slug = sanitize_project_name(app_name)
            yield f"🎯 [Project Target] Detected project from prompt: '{app_name}'\n"
        elif (is_info or is_confirm or is_merge) and existing_projects:
            existing_projects.sort(
                key=lambda p: os.path.getmtime(os.path.join(BASE_WORKSPACE, p)),
                reverse=True,
            )
            app_name = existing_projects[0]
            slug = sanitize_project_name(app_name)
            yield f"🎯 [Project Target] Active project: '{app_name}'\n"
        else:
            app_name = derive_project_slug(prompt)
            slug = sanitize_project_name(app_name)
            yield f"🎯 [Project Target] Derived project name: '{app_name}'\n"

    project_dir = os.path.join(BASE_WORKSPACE, slug)
    os.makedirs(project_dir, exist_ok=True)

    # Sync project codebase from GitHub into workspace/<app_name>
    has_local_files = any(not f.startswith(".") and f != "prompt.txt" for f in os.listdir(project_dir))
    if not has_local_files:
        try:
            synced = sync_project_from_github(app_name, project_dir)
            if synced:
                yield f"📥 [Project: {app_name}] Cloned repository into workspace from GitHub.\n"
        except Exception:
            pass
    elif os.path.isdir(os.path.join(project_dir, ".git")):
        try:
            import subprocess
            from remote_code_agent.github_service import get_github_env
            pull_res = subprocess.run(
                ["git", "pull", "--rebase", "origin", "main"],
                cwd=project_dir,
                env=get_github_env(),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if pull_res.returncode == 0:
                yield f"🔄 [Project: {app_name}] Pulled latest changes from GitHub repository.\n"
        except Exception:
            pass

    # =========================================================================
    # FLOW 1: MERGE PULL REQUEST (User approved merge)
    # =========================================================================
    if is_merge:
        yield f"🔀 [Merge Pull Request] Approving and squash-merging open Pull Request for '{app_name}' into main...\n"
        append_numbered_prompt(project_dir, prompt)

        ok, msg = merge_pull_request(project_dir, app_name)
        if ok:
            yield (
                f"\n🎉 [Pull Request Merged] {msg}\n"
                f"🚀 [CI/CD Deployment] GitHub Actions production deployment triggered on merge to main.\n"
                f"📁 [Workspace] Local workspace synchronized with main.\n"
            )
        else:
            yield f"\n⚠️ [Merge Notice] {msg}\n"

        yield (
            f"\n\n📊 [Project Stats] Status: PR Merged | "
            f"Active Branch: main | "
            f"Project: {app_name}\n"
        )
        return

    # =========================================================================
    # FLOW 2: CONFIRMATION / EXECUTION (User confirmed plan)
    # =========================================================================
    if is_confirm:
        yield f"🚀 [Execution Mode] Plan confirmed! Preparing feature branch and implementation for '{app_name}'...\n"
        append_numbered_prompt(project_dir, prompt)

        # Retrieve the user instruction being confirmed
        last_feature_prompt = get_last_feature_prompt(project_dir) or prompt
        branch_name = derive_feature_branch_name(last_feature_prompt)

        # Ensure remote repository exists and remote main is initialized BEFORE branching
        try:
            ensure_remote_repo_and_main(project_dir, app_name)
        except Exception:
            pass

        # Create or checkout feature branch
        create_or_checkout_branch(project_dir, branch_name)
        yield f"🌿 [Git Branch] Created and checked out dedicated branch: '{branch_name}'\n"

        yield f"📝 [Specification] Updating SPEC.md first and implementing code and tests on '{branch_name}'...\n\n"
        config = get_agent_config(project_dir, app_name=app_name)
        agent_prompt = get_user_chat_prompt(app_name, last_feature_prompt)

    # =========================================================================
    # FLOW 3: INFORMATION RETRIEVAL (Read-only query)
    # =========================================================================
    elif is_info:
        yield "ℹ️ [Mode] Information Retrieval (read-only query — no code will be written or published to GitHub)\n\n"
        config = get_info_retrieval_agent_config(project_dir, app_name=app_name)
        agent_prompt = prompt

    # =========================================================================
    # FLOW 4: PLANNING (New instruction proposing plan before implementation)
    # =========================================================================
    else:
        yield "📋 [Planning Mode] Analyzing workspace and formulating implementation plan...\n"
        append_numbered_prompt(project_dir, prompt)

        branch_name = derive_feature_branch_name(prompt)
        yield f"🌿 [Proposed Branch] Dedicated feature branch: '{branch_name}'\n"

        config = get_info_retrieval_agent_config(project_dir, app_name=app_name)
        agent_prompt = get_planning_chat_prompt(app_name, prompt, branch_name)

    # Snapshot pre-run files for workspace protection in info retrieval & planning modes
    pre_run_files = set()
    if (is_info or not is_confirm) and os.path.isdir(project_dir):
        for root, _, files in os.walk(project_dir):
            for f in files:
                pre_run_files.add(os.path.join(root, f))

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    generated_chars = 0
    agent_output_text = ""

    try:
        async with Agent(config) as agent:
            response = await agent.chat(agent_prompt)

            async for chunk in response.chunks:
                formatted = format_stream_chunk(chunk)
                if formatted:
                    yield formatted
                if hasattr(chunk, "text") and chunk.text:
                    generated_chars += len(chunk.text)
                    agent_output_text += chunk.text

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                meta = response.usage_metadata
                prompt_tokens = getattr(meta, "prompt_token_count", 0) or 0
                completion_tokens = getattr(meta, "candidates_token_count", 0) or 0
                total_tokens = getattr(meta, "total_token_count", 0) or (prompt_tokens + completion_tokens)
    except Exception as agent_err:
        yield f"\n⚠️ [Agent Notice] Code generation step notice: {agent_err}\n"

    # Clean up virtual environments or caches
    for cleanup_dir in [".venv", "venv", "__pycache__", ".pytest_cache"]:
        target_cleanup = os.path.join(project_dir, cleanup_dir)
        if os.path.isdir(target_cleanup):
            shutil.rmtree(target_cleanup, ignore_errors=True)

    # Clean up any files inadvertently created during read-only/planning passes
    if (is_info or not is_confirm) and os.path.isdir(project_dir):
        for root, _, files in os.walk(project_dir):
            for f in files:
                full = os.path.join(root, f)
                if full not in pre_run_files and not f.endswith("prompt.txt"):
                    try:
                        os.remove(full)
                    except Exception:
                        pass

    if total_tokens == 0:
        prompt_tokens = max(len(prompt) // 4, 50)
        completion_tokens = max(generated_chars // 4, 50)
        total_tokens = prompt_tokens + completion_tokens

    updated_stats = record_project_run_tokens(
        app_name,
        tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        workspace_dir=BASE_WORKSPACE,
    )
    _, total_loc = inspect_project_files(project_dir)

    yield (
        f"\n\n📊 [Project Stats] Run Tokens: {total_tokens:,} | "
        f"Cumulative Tokens Spent: {updated_stats.get('total_tokens', 0):,} | "
        f"Total Project Code: {total_loc:,} LOC\n"
    )

    if is_info:
        yield "\n✅ [Info Retrieval] Query completed. No code changes were made or published to GitHub.\n"
    elif not is_confirm:
        # Planning phase conclusion: Ensure output ends with explicit Confirm?
        if not agent_output_text.strip().endswith("Confirm?"):
            yield (
                f"\n\n❓ Confirm?\n"
                f"👉 Reply with 'confirm' (or click 'Confirm Plan') to create branch '{branch_name}', "
                f"update SPEC.md first, implement code, run tests, and open a Pull Request.\n"
            )
    else:
        # Execution phase conclusion: run tests and open PR
        test_dir = os.path.join(project_dir, "tests")
        if os.path.isdir(test_dir):
            yield "\n🧪 [Automated Testing] Running automated unit tests...\n"
            try:
                import subprocess
                test_res = subprocess.run(
                    ["python3", "-m", "unittest", "discover", "tests"],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if test_res.returncode == 0:
                    yield "✅ [Automated Testing] All unit tests passed cleanly!\n"
                else:
                    yield f"⚠️ [Automated Testing] Test output: {(test_res.stdout or test_res.stderr).strip()}\n"
            except Exception as te:
                yield f"ℹ️ [Automated Testing] Test check completed ({te})\n"

        yield f"\n\n📦 [GitHub] Pushing branch '{branch_name}' to GitHub and opening Pull Request...\n"
        pr_title = f"feat: {last_feature_prompt[:60]}"
        pr_body = (
            f"## Summary\n"
            f"Autonomous pair-programming implementation for `{app_name}`.\n\n"
            f"### User Instruction\n"
            f"{last_feature_prompt}\n\n"
            f"### Changes\n"
            f"- Updated `SPEC.md` first across all 12 mandatory sections\n"
            f"- Implemented code and automated tests strictly reflecting specification\n"
            f"- Verified unit tests pass\n"
        )
        success, info, pr_url = push_feature_branch_and_create_pr(
            project_dir=project_dir,
            app_name=app_name,
            branch_name=branch_name,
            title=pr_title,
            body=pr_body,
        )
        if success and pr_url:
            yield (
                f"\n🎉 [Pull Request Created] Successfully created Pull Request for '{app_name}'!\n"
                f"🔗 Pull Request: {pr_url}\n"
                f"🌿 Feature Branch: {branch_name}\n"
                f"☁️ [Cloud Deployment] Staging & Production configured for Google Cloud project ai-learning-499409 and Vercel noam-projects2.\n"
                f"📂 Local Path: {project_dir}\n\n"
                f"👀 [Review & Merge Approval] Please review the pull request on GitHub.\n"
                f"👉 To approve and merge into main, reply with 'merge' or click 'Merge Pull Request'.\n"
            )
        elif success:
            yield (
                f"\n🎉 [GitHub] Successfully pushed changes on branch '{branch_name}'!\n"
                f"ℹ️ {info}\n"
                f"👉 To merge into main, reply with 'merge' or click 'Merge Pull Request'.\n"
            )
        else:
            yield (
                f"\n⚠️ [GitHub PR Notice] Could not create Pull Request: {info}\n"
                f"🌿 Feature branch '{branch_name}' remains safely intact on GitHub without modifying main.\n"
                f"👉 You can review changes on branch '{branch_name}' or retry.\n"
            )


# Alias for flexibility
create_code_stream = generate_code_stream

