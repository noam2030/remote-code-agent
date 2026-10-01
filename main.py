from fastapi import Body, FastAPI
from fastapi.responses import StreamingResponse
import google.antigravity
from google.antigravity import Agent, LocalAgentConfig

app = FastAPI()


@app.post("/run")
async def run(
    prompt: str = Body(
        ...,
        media_type="text/plain",
        description="Prompt text to send to the Google Antigravity agent",
    )
):

    # Initialize google.antigravity.LocalAgentConfig
    config = google.antigravity.LocalAgentConfig()

    # Stream the resulting text tokens back to the client asynchronously
    async def token_stream():
        async with Agent(config) as agent:
            response = await agent.chat(prompt)
            async for token in response:
                yield token

    return StreamingResponse(token_stream(), media_type="text/plain")
