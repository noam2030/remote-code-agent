from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from remote_code_agent.core.config import (
    CORS_ORIGINS,
    FRONTEND_URL,
    GCP_OUTPUT_PROJECT_ID,
    PORT,
)
from remote_code_agent.services.code_creation import BASE_WORKSPACE, generate_code_stream
from remote_code_agent.services.project_service import (
    delete_project,
    get_project_details,
    get_project_file_content,
    list_projects,
)

app = FastAPI(
    title="Google Antigravity Agent Service (Backend API)",
    description="Autonomous code generation backend with Google Cloud Run & Vercel support",
    version="0.3.0",
)

# Enable CORS for cross-origin frontend deployments (e.g. Vercel, localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint: serves JSON service metadata and API information."""
    return {
        "status": "online",
        "service": "Google Antigravity Agent Service (Backend API)",
        "version": "0.3.0",
        "docs": "/docs",
        "api": "/api",
        "frontend": FRONTEND_URL,
        "workspace": BASE_WORKSPACE,
        "cors_enabled": True,
        "github_publishing": "enabled (direct push to main in remote-code-agent-output)",
        "output_repository": "remote-code-agent-output",
        "output_branch": "main",
        "firestore_database": f"{GCP_OUTPUT_PROJECT_ID} / (default)",
    }


@app.get("/ui")
async def ui():
    """Redirect to the deployed frontend web application on Vercel."""
    return RedirectResponse(url=FRONTEND_URL, status_code=307)


@app.get("/api/health")
async def api_health():
    """Health check endpoint for container orchestrators and load balancers."""
    return {
        "status": "healthy",
        "service": "remote-code-agent-backend",
        "version": "0.3.0",
    }


@app.get("/api/projects")
async def api_list_projects():
    """Lists all available projects from GitHub and local workspace."""
    return list_projects()


@app.get("/api/projects/{project_name}")
async def api_get_project(project_name: str):
    """Gets details, file tree, LOC, token stats, and README for a specific project."""
    details = get_project_details(project_name)
    if not details:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found.")
    return details


@app.get("/api/projects/{project_name}/files/{file_path:path}")
async def api_get_project_file(project_name: str, file_path: str):
    """Retrieves content and metadata for a specific file in a project."""
    try:
        return get_project_file_content(project_name, file_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_name}")
async def api_delete_project(
    project_name: str,
    delete_remote: bool = Query(True, description="Whether to also delete the project directory from GitHub"),
):
    """Deletes a project from the local workspace and optionally from GitHub."""
    success, message = delete_project(project_name, delete_remote=delete_remote)
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {"status": "success", "project": project_name, "message": message}


# Backward-compatible direct /generate and /run routes
@app.get("/generate")
@app.get("/api/generate")
async def generate_legacy_get(
    prompt: str = Query(..., description="Prompt describing the application to generate"),
    project_name: str | None = Query(
        None, description="Optional target project name to create or update"
    ),
):
    """Streaming endpoint for autonomous code generation (GET)."""
    return StreamingResponse(
        generate_code_stream(prompt, project_name=project_name),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/run")
@app.post("/api/generate")
async def run(
    request: Request,
    project: str | None = Query(None),
):
    content_type = request.headers.get("content-type", "")
    target_project = project or request.headers.get("x-project-name")

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        prompt_text = body.get("prompt", "")
        if not target_project:
            target_project = body.get("project") or body.get("project_name")
    else:
        body_bytes = await request.body()
        prompt_text = body_bytes.decode("utf-8")

    if not prompt_text or not prompt_text.strip():
        raise HTTPException(status_code=400, detail="Prompt text cannot be empty.")

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        generate_code_stream(prompt_text, project_name=target_project),
        media_type="text/plain",
        headers=headers,
    )
