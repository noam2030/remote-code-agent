"""FastAPI HTTP server for Google Antigravity Agent Service."""

from fastapi import Body, FastAPI
from fastapi.responses import StreamingResponse

from code_creation import BASE_WORKSPACE, generate_code_stream

app = FastAPI(title="Google Antigravity Agent Service")


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
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        generate_code_stream(prompt), media_type="text/plain", headers=headers
    )
