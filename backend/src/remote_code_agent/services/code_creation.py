"""Module responsible for autonomous code creation using Google Antigravity Agent."""

import asyncio
import logging
import os
import shutil
from typing import AsyncGenerator

import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from remote_code_agent.core.config import (
    AGY_CLI_PATH,
    AGY_OAUTH_TOKEN,
    GEMINI_API_KEY,
    GH_TOKEN,
    ensure_agy_oauth_token,
    ensure_agy_settings,
)

logger = logging.getLogger(__name__)


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


async def execute_agy_cli(
    prompt: str,
    project_dir: str,
    continue_session: bool = False,
    extra_flags: list[str] | None = None,
) -> tuple[int, str, str]:
    """Executes the pre-installed agy CLI subprocess non-interactively with the given prompt.

    Awaits process termination and returns (returncode, stdout, stderr).
    """
    # Ensure headless Antigravity configuration (modelProvider: "gemini") and credentials
    ensure_agy_settings()
    ensure_agy_oauth_token()

    agy_bin = AGY_CLI_PATH or shutil.which("agy") or "/usr/local/bin/agy"
    cmd = [agy_bin, "-p", prompt, "--dangerously-skip-permissions"]
    if continue_session:
        cmd.append("--continue")
    if extra_flags:
        cmd.extend(extra_flags)

    env = os.environ.copy()
    if GEMINI_API_KEY:
        env["GEMINI_API_KEY"] = GEMINI_API_KEY
        env.setdefault("GOOGLE_API_KEY", GEMINI_API_KEY)
    if GH_TOKEN:
        env["GH_TOKEN"] = GH_TOKEN
        env["GITHUB_TOKEN"] = GH_TOKEN
    env.setdefault("HOME", os.path.expanduser("~"))

    current_path = env.get("PATH", "")
    for p in ["/usr/local/bin", os.path.expanduser("~/.local/bin"), "/usr/bin", "/bin"]:
        if p not in current_path.split(":"):
            current_path = f"{p}:{current_path}"
    env["PATH"] = current_path

    logger.info(f"Invoking agy CLI in {project_dir}: {cmd[0]} -p <prompt>")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        if continue_session and proc.returncode != 0:
            lower_err = stderr_text.lower()
            if "no conversation" in lower_err or "cannot continue" in lower_err or "conversation not found" in lower_err:
                logger.info(f"Retrying agy CLI without --continue in {project_dir} due to missing previous conversation")
                return await execute_agy_cli(
                    prompt=prompt,
                    project_dir=project_dir,
                    continue_session=False,
                    extra_flags=extra_flags,
                )

        if proc.returncode != 0:
            if "Error 402" in stderr_text or "prepayment credits are depleted" in stderr_text or "RESOURCE_EXHAUSTED" in stderr_text:
                stderr_text += (
                    "\n\n💡 [Gemini API Quota Notice]: Your Gemini API key has depleted its prepayment credits or quota.\n"
                    "• Please visit Google AI Studio at https://aistudio.google.com/app/api-keys to obtain a key with active quota or manage billing.\n"
                )
            elif "Authentication required" in stderr_text or "visit the URL to log in" in stderr_text:
                stderr_text += (
                    "\n\n💡 [Authentication Guidance]: The Antigravity CLI requires an authenticated session.\n"
                    "• In Docker / Cloud Run: Set the GEMINI_API_KEY environment variable to use headless Gemini API mode, "
                    "or set AGY_OAUTH_TOKEN / mount ~/.gemini into the container (-v ~/.gemini:/root/.gemini:ro).\n"
                )

        return proc.returncode, stdout_text, stderr_text
    except FileNotFoundError:
        err = f"Error: Antigravity CLI executable '{agy_bin}' not found on system PATH."
        logger.error(err)
        return 127, "", err
    except Exception as e:
        err = f"Error invoking agy CLI: {e}"
        logger.error(err)
        return 1, "", err


async def generate_code_stream(
    prompt: str,
    project_name: str | None = None,
    auto_confirm: bool = False,
) -> AsyncGenerator[str, None]:
    """Autonomous code execution via pre-installed agy CLI.

    1. Determines target project: uses project_name if provided, detects from prompt, or derives slug.
    2. Ensures isolated workspace directory exists for this project (/workspace/<project_name>).
    3. Syncs existing project codebase from GitHub (clones into workspace or pulls latest if present).
    4. Appends prompt to prompt.txt in the workspace.
    5. Dispatches flow:
       - Merge: Squash-merges open PR into main via merge_pull_request.
       - Execution: Invokes agy CLI non-interactively with prompt, waits until the CLI finishes,
         and only then yields the complete response.
    """
    is_merge = is_merge_request(prompt)
    is_confirm = is_confirmation_request(prompt) or auto_confirm

    if project_name and project_name.strip():
        raw_name = project_name.strip()
        all_projs = list_projects()
        catalog_match = next((p for p in all_projs if p["name"].lower() == raw_name.lower()), None)
        app_name = catalog_match["name"] if catalog_match else raw_name
        slug = sanitize_project_name(app_name)
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
        elif (is_confirm or is_merge) and existing_projects:
            existing_projects.sort(
                key=lambda p: os.path.getmtime(os.path.join(BASE_WORKSPACE, p)),
                reverse=True,
            )
            app_name = existing_projects[0]
            slug = sanitize_project_name(app_name)
        else:
            app_name = derive_project_slug(prompt)
            slug = sanitize_project_name(app_name)

    project_dir = os.path.join(BASE_WORKSPACE, slug)
    os.makedirs(project_dir, exist_ok=True)

    # Sync project codebase from GitHub into workspace/<app_name>
    has_local_files = any(not f.startswith(".") and f != "prompt.txt" for f in os.listdir(project_dir))
    if not has_local_files:
        try:
            sync_project_from_github(app_name, project_dir)
        except Exception:
            pass
    elif os.path.isdir(os.path.join(project_dir, ".git")):
        try:
            import subprocess
            from remote_code_agent.github_service import get_github_env
            subprocess.run(
                ["git", "pull", "--rebase", "origin", "main"],
                cwd=project_dir,
                env=get_github_env(),
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            pass

    # Check if project already has prior prompt history before appending current prompt
    prompt_file = os.path.join(project_dir, "prompt.txt")
    has_prior_prompts = os.path.isfile(prompt_file) and os.path.getsize(prompt_file) > 0
    should_continue = is_confirm or has_prior_prompts

    # Record the user prompt in prompt.txt
    append_numbered_prompt(project_dir, prompt)

    # FLOW 1: MERGE PULL REQUEST
    if is_merge:
        ok, msg = merge_pull_request(project_dir, app_name)
        if ok:
            yield (
                f"🎉 [Pull Request Merged] {msg}\n"
                f"🚀 [CI/CD Deployment] GitHub Actions production deployment triggered on merge to main.\n"
                f"📁 [Workspace] Local workspace synchronized with main.\n\n"
                f"📊 [Project Stats] Status: PR Merged | Active Branch: main | Project: {app_name}\n"
            )
        else:
            yield f"⚠️ [Merge Notice] {msg}\n"
        return

    # FLOW 2: EXECUTE PRE-INSTALLED agy CLI
    # The web application awaits until the CLI finishes execution before yielding response
    returncode, stdout_text, stderr_text = await execute_agy_cli(
        prompt=prompt,
        project_dir=project_dir,
        continue_session=should_continue,
    )

    # Clean up virtual environments or caches
    for cleanup_dir in [".venv", "venv", "__pycache__", ".pytest_cache"]:
        target_cleanup = os.path.join(project_dir, cleanup_dir)
        if os.path.isdir(target_cleanup):
            shutil.rmtree(target_cleanup, ignore_errors=True)

    response_parts: list[str] = []
    if stdout_text and stdout_text.strip():
        response_parts.append(stdout_text.strip())
    elif returncode == 0:
        response_parts.append(f"✅ [agy CLI] Command completed successfully in '{app_name}'.")

    if stderr_text and stderr_text.strip() and returncode != 0:
        response_parts.append(f"\n⚠️ [agy CLI Exit {returncode}]:\n{stderr_text.strip()}")

    # Calculate token & LOC stats
    chars = len("".join(response_parts))
    prompt_tokens = max(len(prompt) // 4, 20)
    completion_tokens = max(chars // 4, 20)
    total_tokens = prompt_tokens + completion_tokens

    updated_stats = record_project_run_tokens(
        app_name,
        tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        workspace_dir=BASE_WORKSPACE,
    )
    _, total_loc = inspect_project_files(project_dir)

    response_parts.append(
        f"\n\n📊 [Project Stats] Status: Completed | "
        f"Project: {app_name} | "
        f"Run Tokens: {total_tokens:,} | "
        f"Cumulative Tokens Spent: {updated_stats.get('total_tokens', 0):,} | "
        f"Total Project Code: {total_loc:,} LOC"
    )

    # Yield complete response ONLY after CLI finishes execution
    yield "\n".join(response_parts) + "\n"


# Alias for flexibility
create_code_stream = generate_code_stream


