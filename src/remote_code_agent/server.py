from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from remote_code_agent.code_creation import BASE_WORKSPACE, generate_code_stream
from remote_code_agent.project_service import get_project_details, list_projects
from remote_code_agent.web_ui import get_web_ui_html

app = FastAPI(title="Google Antigravity Agent Service")


@app.get("/")
async def root(request: Request, format: str | None = Query(None)):
    accept = request.headers.get("accept", "")
    # Serve Web Application UI if requested by browser or explicit format=html
    if format == "html" or ("text/html" in accept and "application/json" not in accept):
        return HTMLResponse(content=get_web_ui_html())

    return {
        "status": "online",
        "service": "Google Antigravity Agent Service",
        "docs": "/docs",
        "ui": "/ui",
        "workspace": BASE_WORKSPACE,
        "github_publishing": "enabled (direct push to main in remote-code-agent-output)",
        "output_repository": "remote-code-agent-output",
        "output_branch": "main",
    }


@app.get("/ui", response_class=HTMLResponse)
async def ui():
    """Direct route for Web Application dashboard."""
    return HTMLResponse(content=get_web_ui_html())


@app.get("/api/projects")
async def api_list_projects():
    """Lists all available projects from GitHub and local workspace."""
    return list_projects()


@app.get("/api/projects/{project_name}")
async def api_get_project(project_name: str):
    """Gets details, file tree, and README for a specific project."""
    details = get_project_details(project_name)
    if not details:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found.")
    return details


@app.post("/run")
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
