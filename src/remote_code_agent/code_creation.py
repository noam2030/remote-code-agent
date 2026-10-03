"""Module responsible for autonomous code creation using Google Antigravity Agent."""

import os
from typing import AsyncGenerator

import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from remote_code_agent.github_service import derive_project_slug, publish_project_to_github
from remote_code_agent.project_service import sanitize_project_name, sync_project_from_github

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
        system_instructions=(
            f"You are an expert autonomous software engineer working on the project '{target_name}'. "
            "Write complete, production-ready code inside your current project workspace. "
            "Examine any existing files in the workspace and implement the requested changes or new features cleanly. "
            "Every project will be automatically built and deployed live to Google Cloud Run. "
            "Ensure applications provide an interactive web interface or HTTP API (e.g. FastAPI, Flask, Streamlit, or HTML/JS) "
            "or a Dockerfile listening on host 0.0.0.0 and port defined by $PORT (default 8080). "
            "Always include comprehensive automated tests in a tests/ directory and a detailed README.md "
            "explaining the application structure, endpoints, and how to use it. "
            "Ensure all files and dependencies (requirements.txt or package.json) are properly created in your workspace."
        ),
        workspaces=[project_dir],
        policies=[policy.allow_all()],
    )


async def generate_code_stream(
    prompt: str,
    project_name: str | None = None,
) -> AsyncGenerator[str, None]:
    """Autonomous code creation workflow.

    1. Determines target project: uses project_name if provided, or derives slug from prompt.
    2. Ensures isolated workspace directory exists for this project.
    3. Syncs existing project codebase from GitHub if available and directory is empty.
    4. Initializes and configures the Google Antigravity agent.
    5. Runs the agent with the user prompt, streaming thoughts, tool calls, and text.
    6. Automatically commits and publishes the generated project to GitHub in <project_name>/.
    """
    if project_name and project_name.strip():
        app_name = sanitize_project_name(project_name.strip())
        yield f"🎯 [Project Target] Working on project: '{app_name}'\n"
    else:
        app_name = derive_project_slug(prompt)
        yield f"🎯 [Project Target] Derived project name: '{app_name}'\n"

    project_dir = os.path.join(BASE_WORKSPACE, app_name)
    os.makedirs(project_dir, exist_ok=True)

    # If the local directory has no files, sync existing project files from GitHub if available
    has_local_files = any(not f.startswith(".") for f in os.listdir(project_dir))
    if not has_local_files:
        try:
            synced = sync_project_from_github(app_name, project_dir)
            if synced:
                yield f"📥 [Project: {app_name}] Synced existing codebase from GitHub repository.\n"
        except Exception:
            pass

    config = get_agent_config(project_dir, app_name=app_name)

    async with Agent(config) as agent:
        response = await agent.chat(prompt)

        # Stream real-time chunks (ToolCalls, Thoughts, Text)
        async for chunk in response.chunks:
            formatted = format_stream_chunk(chunk)
            if formatted:
                yield formatted

    # Automatic GitHub Commit & Direct Push to main in central output repository
    target_repo_name = os.environ.get("GITHUB_OUTPUT_REPO", "remote-code-agent-output")
    yield f"\n\n📦 [GitHub] Publishing generated code to project '{app_name}' in {target_repo_name} (branch: main)...\n"
    success, info = publish_project_to_github(project_dir, app_name, prompt=prompt)
    if success:
        yield (
            f"\n🎉 [GitHub] Successfully pushed code directly to main in {target_repo_name}!\n"
            f"🔗 Repository: {info}\n"
            f"☁️ [Cloud Run] GitHub Actions is automatically building and deploying the app to Google Cloud.\n"
            f"📂 Local Path: {project_dir}\n"
        )
    else:
        yield f"\n⚠️ [GitHub Notice] {info}\n"


# Alias for flexibility
create_code_stream = generate_code_stream
