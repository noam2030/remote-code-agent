import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from remote_code_agent.core.config import (
    CORS_ORIGINS,
    FRONTEND_URL,
    GCP_OUTPUT_PROJECT_ID,
    PORT,
    SKILLS_REPO_URL,
)
from remote_code_agent.services.agent_prompts import (
    get_loaded_skills,
    load_dynamic_skills,
)
from remote_code_agent.services.code_creation import BASE_WORKSPACE, generate_code_stream
from remote_code_agent.services.project_service import (
    get_project_details,
    get_project_file_content,
    list_projects,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler: dynamically loads skills from remote repository upon app startup."""
    try:
        skills = load_dynamic_skills()
        logger.info(
            f"Successfully loaded {len(skills)} dynamic skills on startup: {list(skills.keys())}"
        )
    except Exception as e:
        logger.warning(f"Failed to load dynamic skills on startup: {e}")
    yield


app = FastAPI(
    title="Google Antigravity Agent Service (Backend API)",
    description="Autonomous code generation backend with Google Cloud Run & Vercel support",
    version="0.3.0",
    lifespan=lifespan,
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
        "github_publishing": "enabled (dedicated repository per project)",
        "output_mode": "dedicated_repositories",
        "output_branch": "main",
        "firestore_database": f"{GCP_OUTPUT_PROJECT_ID} / (default)",
        "skills_source": SKILLS_REPO_URL,
        "loaded_skills": list(get_loaded_skills().keys()),
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
        "skills_source": SKILLS_REPO_URL,
        "loaded_skills": list(get_loaded_skills().keys()),
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



from remote_code_agent.services.run_manager import RunAlreadyInProgressError, run_manager


@app.get("/api/runs/active")
async def api_get_active_run():
    """Returns active or latest run status and accumulated logs."""
    return run_manager.get_active_run()


@app.get("/api/runs/active/stream")
async def api_stream_active_run(
    offset: int = Query(0, ge=0, description="Character offset to start streaming from")
):
    """Streaming endpoint to connect/re-attach to the ongoing or latest run."""
    if not run_manager.current_run:
        raise HTTPException(status_code=404, detail="No active or recent run found")
    return StreamingResponse(
        run_manager.stream_run(offset=offset),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


# Backward-compatible direct /generate and /run routes
@app.get("/generate")
@app.get("/api/generate")
async def generate_legacy_get(
    prompt: str = Query(..., description="Prompt describing the application to generate"),
    project_name: str | None = Query(
        None, description="Optional target project name to create or update"
    ),
    offset: int = Query(0, ge=0, description="Optional character offset"),
):
    """Streaming endpoint for autonomous code generation (GET)."""
    try:
        active_run = run_manager.start_run(
            prompt, project_name=project_name, generator_fn=generate_code_stream
        )
    except RunAlreadyInProgressError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return StreamingResponse(
        run_manager.stream_run(active_run.run_id, offset=offset),
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

    try:
        active_run = run_manager.start_run(
            prompt_text, project_name=target_project, generator_fn=generate_code_stream
        )
    except RunAlreadyInProgressError as e:
        raise HTTPException(status_code=409, detail=str(e))

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        run_manager.stream_run(active_run.run_id),
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )

