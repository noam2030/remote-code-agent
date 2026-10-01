from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import google.antigravity
from google.antigravity import Agent, LocalAgentConfig

app = FastAPI()


@app.post("/run")
async def run(request: Request):
    # Accept a raw text string from the request body
    body = await request.body()
    prompt = body.decode("utf-8")

    # Initialize google.antigravity.LocalAgentConfig
    config = google.antigravity.LocalAgentConfig()

    # Stream the resulting text tokens back to the client asynchronously
    async def token_stream():
        async with Agent(config) as agent:
            response = await agent.chat(prompt)
            async for token in response:
                yield token

    return StreamingResponse(token_stream(), media_type="text/plain")
