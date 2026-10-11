"""API router definitions for Remote Code Agent."""

import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from remote_code_agent.services.code_creation import BASE_WORKSPACE, generate_code_stream
from remote_code_agent.services.project_service import (
    get_project_details,
    get_project_file_content,
    list_projects,
)
from remote_code_agent.services.run_manager import RunAlreadyInProgressError, run_manager

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    project_name: str | None = None


@router.get("/health")
async def health_check():
    """Health check endpoint for container orchestrators and load balancers."""
    return {
        "status": "healthy",
        "service": "remote-code-agent-backend",
        "version": "0.3.0",
    }


@router.get("/projects")
async def api_list_projects():
    """Lists all available projects from GitHub and local workspace."""
    return list_projects()


@router.get("/projects/{project_name}")
async def api_get_project(project_name: str):
    """Gets details, file tree, LOC, token stats, and README for a specific project."""
    details = get_project_details(project_name)
    if not details:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found.")
    return details


@router.get("/projects/{project_name}/files/{file_path:path}")
async def api_get_project_file(project_name: str, file_path: str):
    """Retrieves content and metadata for a specific file in a project."""
    try:
        return get_project_file_content(project_name, file_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_path}' not found in project '{project_name}'",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")


@router.get("/runs/active")
async def api_get_active_run():
    """Returns active or latest run status and accumulated logs."""
    return run_manager.get_active_run()


@router.get("/runs/active/stream")
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


@router.get("/generate")
async def api_generate_get(
    prompt: str = Query(..., description="Prompt describing the application to generate"),
    project_name: str | None = Query(
        None, description="Optional target project name to create or update"
    ),
    offset: int = Query(0, ge=0, description="Optional character offset"),
):
    """Streaming endpoint for autonomous code generation (GET)."""
    try:
        run = run_manager.start_run(
            prompt, project_name=project_name, generator_fn=generate_code_stream
        )
    except RunAlreadyInProgressError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return StreamingResponse(
        run_manager.stream_run(run.run_id, offset=offset),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate")
async def api_generate_post(request: GenerateRequest):
    """Streaming endpoint for autonomous code generation (POST)."""
    try:
        run = run_manager.start_run(
            request.prompt, project_name=request.project_name, generator_fn=generate_code_stream
        )
    except RunAlreadyInProgressError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return StreamingResponse(
        run_manager.stream_run(run.run_id),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )

