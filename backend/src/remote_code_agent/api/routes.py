"""API router definitions for Remote Code Agent."""

import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from remote_code_agent.services.code_creation import BASE_WORKSPACE, generate_code_stream
from remote_code_agent.services.project_service import (
    delete_project,
    get_project_details,
    get_project_file_content,
    list_projects,
)

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


@router.delete("/projects/{project_name}")
async def api_delete_project(project_name: str):
    """Deletes a project locally and deletes its remote GitHub directory."""
    success, message = delete_project(project_name)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message, "project": project_name}


@router.get("/generate")
async def api_generate_get(
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


@router.post("/generate")
async def api_generate_post(request: GenerateRequest):
    """Streaming endpoint for autonomous code generation (POST)."""
    return StreamingResponse(
        generate_code_stream(request.prompt, project_name=request.project_name),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
