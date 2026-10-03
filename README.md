# Remote Code Agent - Antigravity SDK on Cloud Run

A minimal, stateless FastAPI service that runs the [Google Antigravity SDK](https://github.com/google/antigravity) in a containerized environment on Google Cloud Run with real-time asynchronous token streaming.

## 🚀 Live Cloud Run Deployment

- **Project ID**: `remote-code-agent-809502`
- **Service Name**: `remote-code-agent`
- **Region**: `us-central1`
- **Live Service URL**: [https://remote-code-agent-702552270447.us-central1.run.app](https://remote-code-agent-702552270447.us-central1.run.app)
- **Interactive OpenAPI Docs**: [https://remote-code-agent-702552270447.us-central1.run.app/docs](https://remote-code-agent-702552270447.us-central1.run.app/docs)

### Query Live Cloud Run from Terminal

```bash
curl -N -X POST https://remote-code-agent-702552270447.us-central1.run.app/run \
  -H "Content-Type: text/plain" \
  -d "Write a python script called hello.py that prints hello from the cloud and run it."
```

Or connect `chat.sh` to Cloud Run:
```bash
AGENT_URL="https://remote-code-agent-702552270447.us-central1.run.app/run" ./chat.sh
```

---

## Features

- **FastAPI Endpoint (`POST /run`)**: Accepts a raw text prompt in the request body and streams back model response tokens asynchronously using `StreamingResponse(media_type="text/plain")`.
- **Google Antigravity SDK**: Integrates `LocalAgentConfig` and the `Agent` async context manager for autonomous agent workflows.
- **Real-Time Process Streaming**: Streams live tool execution notices (`ToolCall`), thoughts, and token deltas chronologically directly from `response.chunks`.
- **Isolated Workspace**: All agent-generated files are strictly isolated in a designated `workspace/` directory.
- **Optimized for Cloud Run**: Uses `python:3.11-slim` with zero pip caching to minimize cold start times and container footprint.
- **Dynamic Port Resolution**: Binds to `0.0.0.0` on `${PORT:-8080}` as required by Cloud Run.

---

## Project Structure

```text
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── chat.sh
├── main.py
├── src/
│   └── remote_code_agent/
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py
│       ├── code_creation.py
│       ├── code_generator.py
│       ├── github_service.py
│       └── main.py
├── tests/
│   ├── test_code_creation.py
│   └── test_server.py
└── workspace/
```

- `src/remote_code_agent/`: Primary Python package containing the agent service logic.
  - `server.py`: FastAPI server and HTTP endpoint routing (`/`, `/run`).
  - `code_creation.py`: Autonomous code creation workflow, workspace isolation, Antigravity Agent execution, and real-time streaming.
  - `github_service.py`: Automated Git initialization, repository creation, and GitHub publishing.
  - `code_generator.py`: Module alias for backwards-compatibility.
  - `main.py` & `__main__.py`: Package entrypoints.
- `main.py`: Top-level application entrypoint wrapper.
- `pyproject.toml`: Package build configuration using standard `src` layout.
- `Dockerfile`: Container build definition with `PYTHONPATH=/app/src`.
- `tests/`: Automated unit tests for server routing and code creation.
- `chat.sh`: Interactive CLI client script.
- `requirements.txt`: Python package dependencies.
- `.dockerignore`: Excluded local files and build caches.
- `.gitignore`: Excluded environment variables and workspace files.

---

## Local Development

1. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

2. Configure environment variables in `.env`:
   ```bash
   echo 'GEMINI_API_KEY="your-gemini-api-key"' > .env
   echo "GH_TOKEN=\"$(gh auth token)\"" >> .env
   echo 'GITHUB_OUTPUT_REPO="remote-code-agent-output"' >> .env
   ```
   *(Alternatively, generate a Personal Access Token with `repo` scope at https://github.com/settings/tokens)*

3. Start the development server:
   ```bash
   uv run --env-file .env uvicorn remote_code_agent.server:app --host 0.0.0.0 --port 8080
   ```
   Or run directly via python:
   ```bash
   uv run --env-file .env python main.py
   ```

4. Test streaming with `chat.sh`:
   ```bash
   ./chat.sh
   ```
