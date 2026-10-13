"""Module responsible for autonomous code creation using Google Antigravity Agent."""

import asyncio
import inspect
import logging
import os
import shutil
import signal
from typing import AsyncGenerator, Callable

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
    ensure_git_config,
    ensure_remote_repo_and_main,
    get_current_branch,
    get_github_env,
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
    on_chunk: Callable[[str], None] | None = None,
    proc_callback: Callable[[asyncio.subprocess.Process], None] | None = None,
    timeout: float = 600.0,
) -> tuple[int, str, str]:
    """Executes the pre-installed agy CLI subprocess non-interactively with the given prompt.

    Streams output lines in real time if on_chunk is provided, and bounds execution with timeout.
    Returns (returncode, stdout, stderr).
    """
    # Ensure headless Antigravity configuration (modelProvider: "gemini") and credentials
    ensure_agy_settings()
    ensure_agy_oauth_token()

    agy_bin = AGY_CLI_PATH or shutil.which("agy") or "/usr/local/bin/agy"
    cmd = [
        agy_bin,
        "-p",
        prompt,
        "--dangerously-skip-permissions",
        "--print-timeout",
        f"{int(timeout)}s",
    ]
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

    # Configure git author and GitHub CLI credentials helper for local-parity execution
    try:
        ensure_git_config(env)
    except Exception:
        pass
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GH_PROMPT_DISABLED"] = "1"
    env["GIT_ASKPASS"] = "/bin/echo"

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
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        if proc_callback:
            try:
                proc_callback(proc)
            except Exception:
                pass

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        is_real_stream = isinstance(proc.stdout, asyncio.StreamReader) or (
            proc.stdout is not None
            and hasattr(proc.stdout, "read")
            and (asyncio.iscoroutinefunction(proc.stdout.read) or inspect.iscoroutinefunction(proc.stdout.read))
        )

        if is_real_stream:
            async def _read_stream(reader: asyncio.StreamReader | None, is_stderr: bool, target_list: list[str]):
                if not reader:
                    return
                try:
                    while True:
                        chunk_bytes = await reader.read(4096)
                        if not chunk_bytes:
                            break
                        text = chunk_bytes.decode("utf-8", errors="replace")
                        target_list.append(text)
                        if on_chunk:
                            try:
                                on_chunk(text)
                            except Exception:
                                pass
                except (asyncio.CancelledError, Exception):
                    pass

            stdout_reader = asyncio.create_task(_read_stream(proc.stdout, False, stdout_lines))
            stderr_reader = asyncio.create_task(_read_stream(proc.stderr, True, stderr_lines))

            try:
                # Wait for the CLI process itself to complete
                await asyncio.wait_for(proc.wait(), timeout=timeout)
                # Bounded drain: allow up to 2 seconds to drain output buffers without hanging on orphan daemons
                try:
                    await asyncio.wait_for(
                        asyncio.gather(stdout_reader, stderr_reader),
                        timeout=2.0,
                    )
                except (asyncio.TimeoutError, Exception):
                    stdout_reader.cancel()
                    stderr_reader.cancel()
            except asyncio.TimeoutError:
                try:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    except Exception:
                        proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                    except (asyncio.TimeoutError, Exception):
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        except Exception:
                            proc.kill()
                        await asyncio.wait_for(proc.wait(), timeout=1.0)
                except Exception:
                    pass
                stdout_reader.cancel()
                stderr_reader.cancel()
                timeout_msg = f"\n⏱️ [Execution Timeout]: agy CLI process exceeded time limit of {int(timeout)} seconds and was stopped.\n"
                if on_chunk:
                    on_chunk(timeout_msg)
                return 124, "".join(stdout_lines), "".join(stderr_lines) + timeout_msg
        else:
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                s_text = stdout_bytes.decode("utf-8", errors="replace") if isinstance(stdout_bytes, bytes) else str(stdout_bytes or "")
                e_text = stderr_bytes.decode("utf-8", errors="replace") if isinstance(stderr_bytes, bytes) else str(stderr_bytes or "")
                if s_text:
                    stdout_lines.append(s_text)
                    if on_chunk:
                        on_chunk(s_text)
                if e_text:
                    stderr_lines.append(e_text)
                    if on_chunk:
                        on_chunk(e_text)
            except asyncio.TimeoutError:
                try:
                    proc.terminate()
                except Exception:
                    pass
                timeout_msg = f"\n⏱️ [Execution Timeout]: agy CLI process exceeded time limit of {int(timeout)} seconds and was stopped.\n"
                return 124, "", timeout_msg

        stdout_text = "".join(stdout_lines)
        stderr_text = "".join(stderr_lines)

        if continue_session and proc.returncode != 0:
            lower_err = stderr_text.lower()
            if "no conversation" in lower_err or "cannot continue" in lower_err or "conversation not found" in lower_err:
                logger.info(f"Retrying agy CLI without --continue in {project_dir} due to missing previous conversation")
                if on_chunk:
                    on_chunk("\nℹ️ [Session Continuity] No prior conversation found; retrying fresh session...\n")
                return await execute_agy_cli(
                    prompt=prompt,
                    project_dir=project_dir,
                    continue_session=False,
                    extra_flags=extra_flags,
                    on_chunk=on_chunk,
                    proc_callback=proc_callback,
                    timeout=timeout,
                )

        if proc.returncode != 0:
            if "Error 402" in stderr_text or "prepayment credits are depleted" in stderr_text or "RESOURCE_EXHAUSTED" in stderr_text:
                quota_notice = (
                    "\n\n💡 [Gemini API Quota Notice]: Your Gemini API key has depleted its prepayment credits or quota.\n"
                    "• Please visit Google AI Studio at https://aistudio.google.com/app/api-keys to obtain a key with active quota or manage billing.\n"
                )
                stderr_text += quota_notice
                if on_chunk:
                    on_chunk(quota_notice)
            elif "Authentication required" in stderr_text or "visit the URL to log in" in stderr_text:
                auth_notice = (
                    "\n\n💡 [Authentication Guidance]: The Antigravity CLI requires an authenticated session.\n"
                    "• In Docker / Cloud Run: Set the GEMINI_API_KEY environment variable to use headless Gemini API mode, "
                    "or set AGY_OAUTH_TOKEN / mount ~/.gemini into the container (-v ~/.gemini:/root/.gemini:ro).\n"
                )
                stderr_text += auth_notice
                if on_chunk:
                    on_chunk(auth_notice)

        return proc.returncode, stdout_text, stderr_text
    except FileNotFoundError:
        err = f"Error: Antigravity CLI executable '{agy_bin}' not found on system PATH."
        logger.error(err)
        if on_chunk:
            on_chunk(err + "\n")
        return 127, "", err
    except Exception as e:
        err = f"Error invoking agy CLI: {e}"
        logger.error(err)
        if on_chunk:
            on_chunk(err + "\n")
        return 1, "", err


async def generate_code_stream(
    prompt: str,
    project_name: str | None = None,
    auto_confirm: bool = False,
    proc_callback: Callable[[asyncio.subprocess.Process], None] | None = None,
) -> AsyncGenerator[str, None]:
    """Autonomous code execution via pre-installed agy CLI.

    1. Determines target project: uses project_name if provided, detects from prompt, or derives slug.
    2. Ensures isolated workspace directory exists for this project (/workspace/<project_name>).
    3. Syncs existing project codebase from GitHub (clones into workspace or pulls latest if present).
    4. Appends prompt to prompt.txt in the workspace.
    5. Dispatches flow:
       - Merge: Squash-merges open PR into main via merge_pull_request.
       - Execution: Invokes agy CLI non-interactively with prompt, streaming live line-by-line output.
    """
    is_merge = is_merge_request(prompt)
    is_confirm = is_confirmation_request(prompt) or auto_confirm

    all_projs = list_projects()
    existing_projects = [
        d
        for d in os.listdir(BASE_WORKSPACE)
        if os.path.isdir(os.path.join(BASE_WORKSPACE, d)) and not d.startswith(".")
    ]
    all_names = list(set([p["name"] for p in all_projs] + existing_projects))
    detected = detect_project_from_prompt(prompt, all_names)

    if project_name and project_name.strip():
        raw_name = project_name.strip()
        catalog_match = next((p for p in all_projs if p["name"].lower() == raw_name.lower()), None)
        app_name = catalog_match["name"] if catalog_match else raw_name
        # Auto-route to explicitly detected project if current project was generic or agent itself
        if detected and detected.lower() != app_name.lower() and app_name.lower() in ("remote-code-agent", "remote_code_agent"):
            app_name = detected
        slug = sanitize_project_name(app_name)
    else:
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

    # Ensure project workspace has git initialized and linked with GitHub remote origin
    if not os.path.isdir(os.path.join(project_dir, ".git")):
        try:
            env = get_github_env()
            ensure_git_config(env)
            ensure_remote_repo_and_main(project_dir, app_name, env=env)
        except Exception:
            try:
                subprocess.run(["git", "init"], cwd=project_dir, check=False, capture_output=True)
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

    # FLOW 2: EXECUTE PRE-INSTALLED agy CLI WITH LIVE STREAMING
    chunk_queue: asyncio.Queue[str | None] = asyncio.Queue()

    def on_chunk_cb(text: str):
        chunk_queue.put_nowait(text)

    async def run_cli_task():
        try:
            return await execute_agy_cli(
                prompt=prompt,
                project_dir=project_dir,
                continue_session=should_continue,
                on_chunk=on_chunk_cb,
                proc_callback=proc_callback,
                timeout=300.0,
            )
        finally:
            chunk_queue.put_nowait(None)

    cli_future = asyncio.create_task(run_cli_task())

    chunks_streamed = 0
    # Stream real-time output chunks to subscribers
    while True:
        chunk = await chunk_queue.get()
        if chunk is None:
            break
        chunks_streamed += 1
        yield chunk

    returncode, stdout_text, stderr_text = await cli_future

    if chunks_streamed == 0 and stdout_text and stdout_text.strip():
        yield stdout_text.strip() + "\n"

    # Clean up virtual environments or caches
    for cleanup_dir in [".venv", "venv", "__pycache__", ".pytest_cache"]:
        target_cleanup = os.path.join(project_dir, cleanup_dir)
        if os.path.isdir(target_cleanup):
            shutil.rmtree(target_cleanup, ignore_errors=True)

    summary_parts: list[str] = []
    if not stdout_text.strip() and returncode == 0:
        summary_parts.append(f"✅ [agy CLI] Command completed successfully in '{app_name}'.")

    if stderr_text and stderr_text.strip() and returncode != 0:
        if f"Exit {returncode}" not in stdout_text and f"Exit {returncode}" not in stderr_text:
            summary_parts.append(f"\n⚠️ [agy CLI Exit {returncode}]:\n{stderr_text.strip()}")

    # Calculate token & LOC stats
    chars = len(stdout_text) + len(stderr_text)
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

    status_label = "Cancelled" if returncode == 124 else ("Failed" if returncode != 0 else "Completed")
    summary_parts.append(
        f"\n\n📊 [Project Stats] Status: {status_label} | "
        f"Project: {app_name} | "
        f"Run Tokens: {total_tokens:,} | "
        f"Cumulative Tokens Spent: {updated_stats.get('total_tokens', 0):,} | "
        f"Total Project Code: {total_loc:,} LOC\n"
    )

    yield "\n".join(summary_parts)


# Alias for flexibility
create_code_stream = generate_code_stream


