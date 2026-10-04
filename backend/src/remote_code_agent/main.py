"""Entrypoint for the Google Antigravity Agent Service."""

import os
import uvicorn

from remote_code_agent.server import app


def main():
    """Runs the FastAPI server with uvicorn."""
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("remote_code_agent.server:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
