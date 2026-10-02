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

- `main.py`: FastAPI server and `/run` streaming handler.
- `github_service.py`: Automated Git initialization, repo creation, and GitHub publishing.
- `Dockerfile`: Container build definition.
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

2. Add your Gemini API key to `.env`:
   ```bash
   echo 'GEMINI_API_KEY="your-api-key"' > .env
   ```

3. Start the development server:
   ```bash
   uv run --env-file .env uvicorn main:app --host 0.0.0.0 --port 8080
   ```

4. Test streaming with `chat.sh`:
   ```bash
   ./chat.sh
   ```
