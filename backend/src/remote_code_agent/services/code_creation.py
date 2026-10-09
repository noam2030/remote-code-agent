"""Module responsible for autonomous code creation using Google Antigravity Agent."""

import os
from typing import AsyncGenerator

import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from remote_code_agent.github_service import derive_project_slug, publish_project_to_github
from remote_code_agent.project_service import (
    inspect_project_files,
    record_project_run_tokens,
    sanitize_project_name,
    sync_project_from_github,
)
from remote_code_agent.prompt_service import update_project_master_prompt
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
        system_instructions=(
            f"You are Antigravity CLI on cloud. Act exactly as Antigravity CLI does. "
            f"When asked to build an application, write the code, push it to my GitHub repository with the name of the project ('{target_name}') and, "
            f"if asked to deploy, add GitHub workflow to deploy. "
            "You can use ai-learning Google Cloud project and Vercel noam-projects2.\n\n"
            f"Operational Guidelines for Project '{target_name}':\n"
            "- Write complete, production-ready code inside your current project workspace.\n"
            "- Examine any existing files in the workspace and implement the requested changes or new features cleanly.\n"
            "- Ensure applications provide an interactive web interface or HTTP API (e.g. FastAPI, Flask, Streamlit, Express, React, or HTML/JS) "
            "or a Dockerfile listening on host 0.0.0.0 and port defined by $PORT (default 8080).\n\n"
            "DEPLOYMENT WORKFLOWS:\n"
            "- If asked to deploy, add automated GitHub Actions workflows in `.github/workflows/` (e.g. `.github/workflows/deploy.yml` or `.github/workflows/deploy-prod.yml`):\n"
            "  * For Google Cloud Platform: Deploy containerized applications to Google Cloud Run in Google Cloud project 'ai-learning-499409' (region: 'us-central1', unauthenticated access, using secrets.GCP_SA_KEY).\n"
            "  * For Vercel: Deploy web applications to Vercel team/scope 'noam-projects2' (e.g. using vercel-action or vercel CLI with secrets.VERCEL_TOKEN).\n\n"
            "PERSISTENCE & DATA STORAGE:\n"
            f"- Any persistent data for this app (such as database records, user input, state, items, notes, tasks) "
            f"MUST be stored in Google Cloud Firestore as a collection in Google Cloud (project 'ai-learning-499409'). "
            f"Use a dedicated collection for this app, named '{target_name}' or '{target_name}_<entity>'. "
            "NEVER use ephemeral local SQLite or local filesystem files for persistent application data on Google Cloud Run, "
            "as local files are destroyed when Cloud Run instances restart or scale down. "
            "Use the official Google Cloud Firestore client library (`google-cloud-firestore` in Python, `@google-cloud/firestore` in Node.js) "
            "with Application Default Credentials (ADC) against database '(default)' in project 'ai-learning-499409' "
            "(read from GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT environment variable with fallback to 'ai-learning-499409'). "
            "Ensure `google-cloud-firestore` is included in requirements.txt (or `@google-cloud/firestore` in package.json). "
            "Always include graceful local fallback or mocking (e.g., an in-memory dictionary or mock store when GCP credentials are not present locally) "
            "so automated unit tests run and pass offline without needing active cloud credentials.\n\n"
            "- Always include comprehensive automated tests in a tests/ directory and a detailed README.md "
            "explaining the application structure, endpoints, Firestore data structure, configuration, and deployment instructions.\n"
            "- Ensure all files and dependencies (requirements.txt or package.json) are properly created in your workspace."
        ),
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
        system_instructions=(
            f"You are an expert software engineer and code analyst inspecting the project '{target_name}'. "
            "The user is asking an informational query to inspect files, understand the architecture, or answer questions. "
            "CRITICAL CONSTRAINTS:\n"
            "- Do NOT create, write, modify, or delete any files or directories in the workspace.\n"
            "- Do NOT write code to disk or execute commands that alter the repository.\n"
            "- Read and inspect existing workspace files as needed to answer the user's question accurately.\n"
            "- Provide a direct, thorough, and well-structured answer in your response text in the console."
        ),
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
    3. Ensures isolated workspace directory exists for this project.
    4. Syncs existing project codebase from GitHub if available and directory is empty.
    5. If info retrieval:
       - Runs read-only agent to inspect files and answer the question.
       - Does NOT update prompt.txt.
       - Does NOT publish to GitHub.
       - Protects workspace against any accidental alterations.
       - Replies directly in the console stream.
    6. If code creation:
       - Consolidates prompt.txt specification.
       - Runs code generation agent to implement requested changes.
       - Automatically commits and publishes the generated project to GitHub main.
    """
    is_info = is_info_retrieval_request(prompt)

    if project_name and project_name.strip():
        app_name = sanitize_project_name(project_name.strip())
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
            yield f"🎯 [Project Target] Detected project from prompt: '{app_name}'\n"
        elif is_info and existing_projects:
            # Default to the most recently modified project for informational inspection
            existing_projects.sort(
                key=lambda p: os.path.getmtime(os.path.join(BASE_WORKSPACE, p)),
                reverse=True,
            )
            app_name = existing_projects[0]
            yield f"🎯 [Project Target] Inspecting active project: '{app_name}'\n"
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

    agent_prompt = (
        f"You are Antigravity CLI on cloud. Act exactly as Antigravity CLI does. "
        f"When asked to build an application, write the code, push it to my GitHub repository with the name of the project ('{app_name}') and, "
        f"if asked to deploy, add GitHub workflow to deploy. You can use ai-learning Google Cloud project and Vercel noam-projects2.\n\n"
        f"User Instruction:\n{prompt}"
    ) if not is_info else prompt

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
