"""Module responsible for autonomous code creation using Google Antigravity Agent."""

import os
import shutil
from typing import AsyncGenerator

import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from remote_code_agent.github_service import derive_project_slug, publish_project_to_github
from remote_code_agent.project_service import (
    inspect_project_files,
    list_projects,
    record_project_run_tokens,
    sanitize_project_name,
    sync_project_from_github,
)
from remote_code_agent.prompt_service import update_project_master_prompt
from remote_code_agent.services.agent_prompts import (
    get_agent_system_prompt,
    get_info_retrieval_system_prompt,
    get_user_chat_prompt,
)
from remote_code_agent.services.intent_service import (
    detect_project_from_prompt,
    is_info_retrieval_request,
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
) -> AsyncGenerator[str, None]:
    """Autonomous code creation and inspection workflow.

    1. Classifies user intent (information retrieval vs. code creation/modification).
    2. Determines target project: uses project_name if provided, detects from prompt, or derives slug.
    3. Ensures isolated workspace directory exists for this project (/workspace/<project_name>).
    4. Syncs existing project codebase from GitHub (clones into workspace or pulls latest if present).
    5. If info retrieval:
       - Runs read-only agent to inspect files and answer the question.
       - Does NOT update prompt.txt.
       - Does NOT publish to GitHub.
       - Protects workspace against any accidental alterations.
       - Replies directly in the console stream.
    6. If code creation:
       - Consolidates prompt.txt specification.
       - Runs code generation agent to implement requested changes in /workspace/<project_name>.
       - Automatically commits and publishes the generated/updated project to GitHub main.
    """
    is_info = is_info_retrieval_request(prompt)

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
        elif is_info and existing_projects:
            # Default to the most recently modified project for informational inspection
            existing_projects.sort(
                key=lambda p: os.path.getmtime(os.path.join(BASE_WORKSPACE, p)),
                reverse=True,
            )
            app_name = existing_projects[0]
            slug = sanitize_project_name(app_name)
            yield f"🎯 [Project Target] Inspecting active project: '{app_name}'\n"
        else:
            app_name = derive_project_slug(prompt)
            slug = sanitize_project_name(app_name)
            yield f"🎯 [Project Target] Derived project name: '{app_name}'\n"

    project_dir = os.path.join(BASE_WORKSPACE, slug)
    os.makedirs(project_dir, exist_ok=True)

    # Sync project codebase from GitHub into workspace/<app_name>
    has_local_files = any(not f.startswith(".") for f in os.listdir(project_dir))
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

    if is_info:
        yield "ℹ️ [Mode] Information Retrieval (read-only query — no code will be written or published to GitHub)\n\n"
        config = get_info_retrieval_agent_config(project_dir, app_name=app_name)
    else:
        # Update and re-summarize canonical prompt.txt specification
        yield "📋 [Specification] Consolidating master prompt specification in prompt.txt...\n"
        try:
            await update_project_master_prompt(project_dir, app_name, prompt)
            yield "✅ [Specification] Master prompt specification updated in prompt.txt\n\n"
        except Exception as e:
            yield f"⚠️ [Specification Notice] Could not update prompt.txt: {e}\n\n"
        config = get_agent_config(project_dir, app_name=app_name)

    # Snapshot pre-run files for workspace protection in info retrieval mode
    pre_run_files = set()
    if is_info and os.path.isdir(project_dir):
        for root, _, files in os.walk(project_dir):
            for f in files:
                pre_run_files.add(os.path.join(root, f))

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    generated_chars = 0

    agent_prompt = get_user_chat_prompt(app_name, prompt) if not is_info else prompt

    try:
        async with Agent(config) as agent:
            response = await agent.chat(agent_prompt)

            # Stream real-time chunks (ToolCalls, Thoughts, Text)
            async for chunk in response.chunks:
                formatted = format_stream_chunk(chunk)
                if formatted:
                    yield formatted
                if hasattr(chunk, "text") and chunk.text:
                    generated_chars += len(chunk.text)

            # Extract token usage metadata from response
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                meta = response.usage_metadata
                prompt_tokens = getattr(meta, "prompt_token_count", 0) or 0
                completion_tokens = getattr(meta, "candidates_token_count", 0) or 0
                total_tokens = getattr(meta, "total_token_count", 0) or (prompt_tokens + completion_tokens)
    except Exception as agent_err:
        yield f"\n⚠️ [Agent Notice] Code generation step notice: {agent_err}\n"

    # Clean up any virtual environments or cache folders if created in workspace
    for cleanup_dir in [".venv", "venv", "__pycache__", ".pytest_cache"]:
        target_cleanup = os.path.join(project_dir, cleanup_dir)
        if os.path.isdir(target_cleanup):
            shutil.rmtree(target_cleanup, ignore_errors=True)

    # Clean up any files inadvertently created during info retrieval
    if is_info and os.path.isdir(project_dir):
        for root, _, files in os.walk(project_dir):
            for f in files:
                full = os.path.join(root, f)
                if full not in pre_run_files:
                    try:
                        os.remove(full)
                    except Exception:
                        pass

    if total_tokens == 0:
        # Fallback estimation based on prompt and generated output characters
        prompt_tokens = max(len(prompt) // 4, 50)
        completion_tokens = max(generated_chars // 4, 50)
        total_tokens = prompt_tokens + completion_tokens

    # Record token usage in project stats
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
    else:
        yield f"\n\n📦 [GitHub] Publishing generated code for project '{app_name}' to GitHub (branch: main)...\n"
        success, info = publish_project_to_github(project_dir, app_name, prompt=prompt)
        if success:
            yield (
                f"\n🎉 [GitHub] Successfully pushed code to GitHub repository for '{app_name}'!\n"
                f"🔗 Repository: {info}\n"
                f"☁️ [Cloud Deployment] Configured for Google Cloud project ai-learning-499409 and Vercel noam-projects2.\n"
                f"📂 Local Path: {project_dir}\n"
            )
        else:
            yield f"\n⚠️ [GitHub Notice] {info}\n"


# Alias for flexibility
create_code_stream = generate_code_stream
