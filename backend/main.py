"""Top-level entrypoint for backend service."""

from remote_code_agent.server import app
from remote_code_agent.main import main

__all__ = ["app", "main"]

if __name__ == "__main__":
    main()
