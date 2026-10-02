"""Configuration and environment variable management."""

import os
from pathlib import Path


def load_env_file(dotenv_path: str | Path | None = None) -> None:
    """Loads environment variables from a .env file into os.environ if not already set.

    Searches in current working directory and repository root if dotenv_path is not specified.
    """
    if dotenv_path is None:
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
        ]
        for candidate in candidates:
            if candidate.is_file():
                dotenv_path = candidate
                break

    if not dotenv_path or not Path(dotenv_path).is_file():
        return

    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


# Automatically load on import
load_env_file()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
AGENT_WORKSPACE = os.environ.get("AGENT_WORKSPACE", "workspace")
PORT = int(os.environ.get("PORT", 8080))
