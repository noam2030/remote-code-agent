# Remote Code Agent - Backend Service

FastAPI backend service running the Google Antigravity autonomous agent on Google Cloud Run.

## Architecture & Structure

```
backend/
├── src/remote_code_agent/
│   ├── api/               # API endpoints (/api/projects, /api/health, etc.)
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/              # Core configuration & environment variables
│   │   ├── __init__.py
│   │   └── config.py
│   ├── services/          # Core business services
│   │   ├── __init__.py
│   │   ├── code_creation.py
│   │   ├── github_service.py
│   │   ├── project_service.py
│   │   └── prompt_service.py
│   ├── main.py            # Local development CLI entrypoint
│   └── server.py          # FastAPI application with CORS middleware
├── tests/                 # Comprehensive unit & integration tests
├── Dockerfile             # Container configuration for Cloud Run
├── pyproject.toml         # Package definition and dependencies
└── requirements.txt
```

## Running Locally

```bash
cd backend
uv run python -m remote_code_agent.main
```
Or:
```bash
uvicorn remote_code_agent.server:app --reload --port 8080
```

## Running Tests

```bash
cd backend
PYTHONPATH=src uv run python -m unittest discover tests
```
