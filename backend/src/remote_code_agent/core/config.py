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
            Path(__file__).resolve().parent.parent.parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent.parent.parent / ".env",
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

import shutil

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
AGY_CLI_PATH = (
    os.environ.get("AGY_CLI_PATH")
    or shutil.which("agy")
    or "/usr/local/bin/agy"
)
AGY_OAUTH_TOKEN = os.environ.get("AGY_OAUTH_TOKEN") or os.environ.get("JETSKI_OAUTH_TOKEN", "")


def ensure_agy_oauth_token() -> bool:
    """Ensures ~/.gemini/jetski-standalone-oauth-token exists.

    If AGY_OAUTH_TOKEN environment variable is set, writes it to
    ~/.gemini/jetski-standalone-oauth-token with 0600 permissions.
    Returns True if the token file exists and is populated, False otherwise.
    """
    token_path = Path.home() / ".gemini" / "jetski-standalone-oauth-token"
    if AGY_OAUTH_TOKEN and AGY_OAUTH_TOKEN.strip():
        try:
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(AGY_OAUTH_TOKEN.strip(), encoding="utf-8")
            token_path.chmod(0o600)
            return True
        except Exception:
            pass
    return token_path.is_file() and token_path.stat().st_size > 0


# Ensure token file is populated if env var is available
ensure_agy_oauth_token()

AGENT_WORKSPACE = os.environ.get("AGENT_WORKSPACE", "workspace")

SKILLS_REPO_URL = os.environ.get(
    "SKILLS_REPO_URL",
    "https://github.com/noam2030/build-with-agent/tree/main/.agents/skills",
)
GITHUB_OUTPUT_REPO = os.environ.get("GITHUB_OUTPUT_REPO", "")
GCP_OUTPUT_PROJECT_ID = (
    os.environ.get("GCP_OUTPUT_PROJECT_ID")
    or os.environ.get("GCP_PROJECT_ID")
    or "ai-learning-499409"
)
VERCEL_SCOPE = os.environ.get("VERCEL_SCOPE", "noam-projects2")
VERCEL_TEAM = os.environ.get("VERCEL_TEAM", "noam-projects2")
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "")
VERCEL_ORG_ID = os.environ.get("VERCEL_ORG_ID", "")
VERCEL_PROJECT_ID = os.environ.get("VERCEL_PROJECT_ID", "")
GCP_SA_KEY = os.environ.get("GCP_SA_KEY", "")
PORT = int(os.environ.get("PORT", 8080))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "*,http://localhost:3000,http://localhost:5173,http://localhost:8080",
    ).split(",")
    if origin.strip()
]
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL", "https://remote-code-agent-ui.vercel.app"
)
