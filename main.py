import os
from fastapi import Body, FastAPI
from fastapi.responses import StreamingResponse
import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from github_service import derive_project_slug, publish_project_to_github

app = FastAPI(title="Google Antigravity Agent Service")

# Dedicated workspace directory for agent-generated projects
BASE_WORKSPACE = os.path.abspath(os.environ.get("AGENT_WORKSPACE", "workspace"))
os.makedirs(BASE_WORKSPACE, exist_ok=True)



@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Google Antigravity Agent Service",
        "docs": "/docs",
        "workspace": BASE_WORKSPACE,
        "github_publishing": "enabled (new standalone repo per app)",
    }


@app.post("/run")
async def run(
    prompt: str = Body(
        ...,
        media_type="text/plain",
        description="Prompt text to send to the Google Antigravity agent",
    )
):
    # Create an isolated project directory for this application
    app_name = derive_project_slug(prompt)
    project_dir = os.path.join(BASE_WORKSPACE, app_name)
    os.makedirs(project_dir, exist_ok=True)

    # Configure agent with the isolated workspace and autonomous permissions
    config = google.antigravity.LocalAgentConfig(
        system_instructions=(
            "You are an expert autonomous software engineer. "
            "Write complete, production-ready code inside your current project workspace. "
            "Always include a detailed README.md explaining the application structure and how to run it. "
            "Ensure all files and dependencies are properly created in your workspace."
        ),
        workspaces=[project_dir],
        policies=[policy.allow_all()],
    )

    async def token_stream():
        async with Agent(config) as agent:
            response = await agent.chat(prompt)

            # Stream real-time chunks (ToolCalls, Thoughts, Text)
            async for chunk in response.chunks:
                if isinstance(chunk, types.Thought):
                    yield f"💭 {chunk.text}"
                elif isinstance(chunk, types.ToolCall):
                    target = (
                        chunk.args.get("file_path")
                        or chunk.args.get("command_line")
                        or chunk.args.get("TargetFile")
                        or chunk.args.get("CommandLine")
                        or ""
                    )
                    detail = f" -> {os.path.basename(target)}" if target else ""
                    yield f"\n⚡ [Tool: {chunk.name}{detail}]\n"
                elif isinstance(chunk, types.Text):
                    yield chunk.text

        # Automatic GitHub Commit & Push after generation completes
        yield f"\n\n📦 [GitHub] Initializing Git repository and publishing to GitHub ({app_name})...\n"
        success, info = publish_project_to_github(project_dir, app_name)
        if success:
            yield (
                f"\n🎉 [GitHub] Successfully pushed code to new repository!\n"
                f"🔗 Repository URL: {info}\n"
                f"📂 Local Path: {project_dir}\n"
            )
        else:
            yield f"\n⚠️ [GitHub Notice] {info}\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        token_stream(), media_type="text/plain", headers=headers
    )
