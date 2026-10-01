import os
from fastapi import Body, FastAPI
from fastapi.responses import StreamingResponse
import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

app = FastAPI(title="Google Antigravity Agent Service")

# Dedicated workspace directory for agent-generated files
WORKSPACE_DIR = os.path.abspath(os.environ.get("AGENT_WORKSPACE", "workspace"))
os.makedirs(WORKSPACE_DIR, exist_ok=True)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Google Antigravity Agent Service",
        "docs": "/docs",
        "workspace": WORKSPACE_DIR,
    }


@app.post("/run")
async def run(
    prompt: str = Body(
        ...,
        media_type="text/plain",
        description="Prompt text to send to the Google Antigravity agent",
    )
):
    # Configure agent with workspace isolation and full tool permissions
    config = google.antigravity.LocalAgentConfig(
        workspaces=[WORKSPACE_DIR],
        policies=[policy.allow_all()],
    )

    # Stream real-time semantic chunks (ToolCalls, Thoughts, and Text deltas)
    async def token_stream():
        async with Agent(config) as agent:
            response = await agent.chat(prompt)

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

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        token_stream(), media_type="text/plain", headers=headers
    )
