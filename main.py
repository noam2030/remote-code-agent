import asyncio
import os
from fastapi import Body, FastAPI
from fastapi.responses import StreamingResponse
import google.antigravity
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import hooks, policy

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
    event_queue: asyncio.Queue[str] = asyncio.Queue()

    @hooks.pre_tool_call_decide
    async def on_pre_tool(data: types.ToolCall) -> types.HookResult:
        target = (
            data.args.get("TargetFile")
            or data.args.get("AbsolutePath")
            or data.args.get("CommandLine")
            or ""
        )
        detail = f" -> {os.path.basename(target)}" if target else ""
        event_queue.put_nowait(f"\n⚡ [Tool: {data.name}{detail}]\n")
        return types.HookResult(allow=True)

    @hooks.post_tool_call
    async def on_post_tool(data):
        event_queue.put_nowait("✓ [Action complete]\n\n")

    # Initialize google.antigravity.LocalAgentConfig with workspace isolation and hooks
    config = google.antigravity.LocalAgentConfig(
        workspaces=[WORKSPACE_DIR],
        hooks=[on_pre_tool, on_post_tool],
        policies=[policy.allow_all()],
    )

    # Stream thoughts, tool execution events, and response tokens back to client
    async def token_stream():
        async with Agent(config) as agent:
            response = await agent.chat(prompt)

            # Stream thinking thoughts if available
            thought_started = False
            async for thought in response.thoughts:
                if not thought_started:
                    yield "💭 [Thinking]\n"
                    thought_started = True
                while not event_queue.empty():
                    yield event_queue.get_nowait()
                yield thought

            if thought_started:
                yield "\n\n"

            # Stream tool execution notices and model text tokens
            async for token in response:
                while not event_queue.empty():
                    yield event_queue.get_nowait()
                yield token

            # Flush any remaining tool events
            while not event_queue.empty():
                yield event_queue.get_nowait()

    return StreamingResponse(token_stream(), media_type="text/plain")
