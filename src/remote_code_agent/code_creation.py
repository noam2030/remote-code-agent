"""Module responsible for autonomous code creation using Google Antigravity Agent."""

import os
from typing import AsyncGenerator

import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from remote_code_agent.github_service import derive_project_slug, publish_project_to_github

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


def get_agent_config(project_dir: str) -> google.antigravity.LocalAgentConfig:
    """Creates the LocalAgentConfig for code generation in an isolated workspace."""
    return google.antigravity.LocalAgentConfig(
        system_instructions=(
            "You are an expert autonomous software engineer. "
            "Write complete, production-ready code inside your current project workspace. "
            "Always include a detailed README.md explaining the application structure and how to run it. "
            "Ensure all files and dependencies are properly created in your workspace."
        ),
        workspaces=[project_dir],
        policies=[policy.allow_all()],
    )


async def generate_code_stream(prompt: str) -> AsyncGenerator[str, None]:
    """Autonomous code creation workflow.

    1. Derives a project slug and creates an isolated workspace directory.
    2. Initializes and configures the Google Antigravity agent.
    3. Runs the agent with the user prompt, streaming thoughts, tool calls, and text.
    4. Automatically commits and publishes the generated project to GitHub.
    """
    # Create an isolated project directory for this application
    app_name = derive_project_slug(prompt)
    project_dir = os.path.join(BASE_WORKSPACE, app_name)
    os.makedirs(project_dir, exist_ok=True)

    config = get_agent_config(project_dir)

    async with Agent(config) as agent:
        response = await agent.chat(prompt)

        # Stream real-time chunks (ToolCalls, Thoughts, Text)
        async for chunk in response.chunks:
            formatted = format_stream_chunk(chunk)
            if formatted:
                yield formatted

    # Automatic GitHub Commit & Pull Request to central output repository
    target_repo_name = os.environ.get("GITHUB_OUTPUT_REPO", "remote-code-agent-output")
    yield f"\n\n📦 [GitHub] Publishing generated code to {target_repo_name} (branch: feat/{app_name})...\n"
    success, info = publish_project_to_github(project_dir, app_name, prompt=prompt)
    if success:
        yield (
            f"\n🎉 [GitHub] Successfully pushed code to {target_repo_name}!\n"
            f"🔗 Pull Request: {info}\n"
            f"📂 Local Path: {project_dir}\n"
        )
    else:
        yield f"\n⚠️ [GitHub Notice] {info}\n"


# Alias for flexibility
create_code_stream = generate_code_stream
