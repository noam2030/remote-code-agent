# Remote Code Agent - Antigravity SDK on Cloud Run

A minimal, stateless FastAPI service that runs the [Google Antigravity SDK](https://github.com/google/antigravity) in a containerized environment on Google Cloud Run with real-time asynchronous token streaming.

## Features

- **FastAPI Endpoint (`POST /run`)**: Accepts a raw text prompt in the request body and streams back model response tokens asynchronously using `StreamingResponse(media_type="text/plain")`.
- **Google Antigravity SDK**: Integrates `LocalAgentConfig` and the `Agent` async context manager for agent workflows.
- **Optimized for Cloud Run**: Uses `python:3.11-slim` with zero pip caching to minimize cold start times and container footprint.
- **Dynamic Port Resolution**: Binds to `0.0.0.0` on `${PORT:-8080}` as required by Cloud Run.

## Project Structure

- `main.py`: FastAPI server and `/run` streaming handler.
- `Dockerfile`: Container build definition.
- `requirements.txt`: Python package dependencies.
- `.dockerignore`: Excluded local files and build caches.

## Local Development

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Export your Gemini API key:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

3. Start the development server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080 --reload
   ```

4. Test streaming with `curl`:
   ```bash
   curl -N -X POST http://localhost:8080/run \
     -H "Content-Type: text/plain" \
     -d "Write a python function to compute fibonacci numbers."
   ```

## Cloud Run Deployment

1. Build container using Cloud Build:
   ```bash
   gcloud builds submit --tag gcr.io/<PROJECT_ID>/antigravity-agent-service
   ```

2. Deploy service:
   ```bash
   gcloud run deploy antigravity-agent-service \
     --image gcr.io/<PROJECT_ID>/antigravity-agent-service \
     --platform managed \
     --region us-central1 \
     --set-env-vars GEMINI_API_KEY="<YOUR_GEMINI_API_KEY>" \
     --allow-unauthenticated
   ```
