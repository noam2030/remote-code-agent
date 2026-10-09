# Project Specification

## 1. Overview
Remote Code Agent is an autonomous AI-driven code generation, modification, and execution engine operating as **Antigravity CLI on Cloud**, built with the Google Antigravity SDK and FastAPI, paired with a modern React/TypeScript dashboard. The agent acts exactly as Antigravity CLI does on the cloud: when instructed to build an application, it autonomously writes complete production code, pushes it to the user's dedicated GitHub repository named after the project (`noam2030/<project_name>`), and if asked to deploy, adds GitHub Actions deployment workflows targeting Google Cloud project `ai-learning` (`ai-learning-499409`) and Vercel team/scope `noam-projects2`.

The service is deployed on Google Cloud Run under project `ai-learning-499409`.

## 2. Requirements
- **Antigravity CLI on Cloud Logic**: Act exactly as Antigravity CLI on the cloud: reason autonomously, write clean production-ready code, run tests, and manage files in isolated project workspaces.
- **Dedicated Project Repositories**: Commit and push generated application code directly to the user's dedicated GitHub repository named after the project (`<owner>/<project_name>`), creating the repository via GitHub CLI if it does not yet exist.
- **Automated Deployment Workflows**: When asked to deploy, generate GitHub Actions workflows (`.github/workflows/deploy.yml`):
  - Google Cloud Platform deployments target project `ai-learning` (`ai-learning-499409`) on Cloud Run.
  - Vercel deployments target scope/team `noam-projects2`.
- **Cloud Persistence**: Persistent application state uses Google Cloud Firestore in project `ai-learning-499409` under dedicated collections, with mock/in-memory fallbacks for offline testing.
- **Real-Time Streaming**: Stream logs, tool invocations, and agent actions to client applications using Server-Sent Events (SSE).
- **Project Isolation**: Maintain independent workspace directories under `workspace/<project_name>` for each generated or managed project.
- **Prompt History Tracking**: Persist sequential user prompts per project in `prompt.txt` (`1. <prompt>`, `2. <prompt>`).
- **Read-Only / Retrieval Mode**: Support query-only intent detection to inspect repositories without writing code or pushing to GitHub.
- **Continuous Integration & Delivery**: Maintain GitHub Actions workflows for automated test execution, staging deployment on PRs, and production deployment on merge to `main`.

## 3. User Experience
- **Interactive Dashboard**: Clean, responsive web interface allowing users to enter prompts, view active projects, inspect generated file trees, and view live terminal output.
- **Terminal & Log Viewer**: Real-time console view rendering color-coded output from backend SSE streams.
- **Project Navigator**: Sidebar displaying available workspace projects with creation timestamps, file counts, and direct links to GitHub repositories.
- **Execution Controls**: Controls to initiate generation, cancel in-progress operations, or remove projects.

## 4. Architecture
The system consists of two primary tiers:
1. **Frontend**: Single-page application built with React 18, TypeScript, and Vite, deployed to Vercel.
2. **Backend**: Containerized FastAPI service running on Google Cloud Run, communicating with the Google Antigravity SDK and GitHub APIs.

```text
[ React / Vite Frontend (Vercel) ]
             │
             │ HTTPS / SSE
             ▼
[ FastAPI Backend (Google Cloud Run in ai-learning-499409) ]
     ├── Core Configuration (Env, Secrets, Paths)
     ├── API Layer (REST & SSE Endpoints)
     ├── Services
     │    ├── Code Creation (Antigravity SDK Runner)
     │    ├── Intent Detection (Info vs Code)
     │    ├── Project Service (Workspace & Files)
     │    ├── Prompt Service (prompt.txt History)
     │    └── GitHub Service (Repo Init & Push)
     └── Local Storage (workspace/<project_name>)
```

## 5. Technology Stack
- **Backend Language & Runtime**: Python 3.11
- **API Framework**: FastAPI, Uvicorn, Pydantic
- **AI Agent Framework**: Google Antigravity SDK (`google-antigravity`)
- **Version Control & Remote Tools**: Git, GitHub CLI (`gh`)
- **Frontend Framework**: React 18, TypeScript, Vite
- **Cloud Infrastructure**: Google Cloud Platform
  - **Project ID**: `ai-learning-499409`
  - **Hosting**: Google Cloud Run (Fully managed serverless container runtime)
  - **Container Registry**: Artifact Registry (`cloud-run-source-deploy` in `us-central1`)
  - **Build Tool**: Google Cloud Build
- **CI/CD**: GitHub Actions

## 6. Backend
The backend is structured under `backend/src/remote_code_agent`:
- `core/config.py`: Environment variable loading, fallback discovery, GCP project ID (`ai-learning-499409`), and Vercel scope settings (`noam-projects2`).
- `api/routes.py`: FastAPI routes registering `/api/health`, `/api/projects`, `/api/generate`, and file inspection endpoints.
- `services/code_creation.py`: Core agent execution loop utilizing `google.antigravity` configured as Antigravity CLI on Cloud: writes code in workspace, streams tool calls, generates GitHub deployment workflows for GCP (`ai-learning-499409`) and Vercel (`noam-projects2`), and coordinates repository publishing.
- `services/intent_service.py`: Classifies user input into code modification tasks or informational queries.
- `services/project_service.py`: Workspace directory indexing, project deletion, and file metadata generation.
- `services/prompt_service.py`: Parsing, updating, and synthesizing project prompt history in `prompt.txt`.
- `services/github_service.py`: Dedicated project repository creation (`<owner>/<project_name>`), remote git publishing directly to `main`, and central output repository catalog syncing.
- `server.py`: FastAPI application factory with CORS middleware and error handling.

## 7. Frontend
The frontend is structured under `frontend/`:
- `src/components/`: Reusable UI modules including `Header`, `Sidebar`, `Terminal`, `PromptEditor`, `ProjectStats`, and modal dialogs.
- `src/services/api.ts`: Typed HTTP client wrapping backend REST endpoints and EventSource listeners.
- `src/types/`: Interfaces for projects, generation events, file trees, and system status.
- `src/App.tsx`: Top-level application state orchestrator.
- `vercel.json`: Routing and static asset caching configuration.

## 8. Data Model
- **Project Structure**:
  ```text
  workspace/
  └── <project-name>/
      ├── prompt.txt         # Numbered prompt log
      ├── SPEC.md            # Authoritative project spec
      ├── .github/workflows/ # Deployment workflows (if requested)
      └── ...                # Generated source code
  ```
- **SSE Event Protocol**:
  - `data: {"type": "log", "message": "..."}`
  - `data: {"type": "tool_call", "tool": "...", "args": {...}}`
  - `data: {"type": "error", "error": "..."}`
  - `data: {"type": "done", "project": "...", "repo_url": "..."}`

## 9. API
- `GET /api/health`: Health status endpoint returning status code 200 and system health metadata.
- `GET /api/projects`: List all managed projects in the workspace.
- `DELETE /api/projects/{name}`: Delete project workspace directory.
- `GET /api/projects/{name}/files`: Retrieve file tree and contents for a specific project.
- `POST /api/generate`: Initiate code generation or prompt execution, returning an SSE stream.
- `GET /api/projects/{name}/prompts`: Retrieve history of prompts for the specified project.

## 10. Configuration
The application relies on the following environment variables:
- `GEMINI_API_KEY`: API key for Gemini models and Google Antigravity SDK.
- `GH_TOKEN` / `GITHUB_TOKEN`: GitHub personal access token with `repo` scope for repository management.
- `AGENT_WORKSPACE`: Relative or absolute path to the local project workspace (default: `workspace`).
- `GITHUB_OUTPUT_REPO`: Default GitHub repository name for central output catalog.
- `GCP_OUTPUT_PROJECT_ID`: Target Google Cloud Project ID (`ai-learning-499409`).
- `VERCEL_SCOPE`: Target Vercel team/scope for deployments (`noam-projects2`).
- `PORT`: HTTP port for backend server (default: `8080`).
- `CORS_ORIGINS`: Comma-separated list of allowed origins.
- `FRONTEND_URL`: URL of the deployed frontend application (`https://remote-code-agent-ui.vercel.app`).
- `VITE_API_URL`: Frontend environment variable defining the backend API URL (production: `https://remote-code-agent-289332143182.us-central1.run.app`).

## 11. Testing
- Automated unit and integration tests are placed in `backend/tests/`.
- Test execution command: `.venv/bin/python -m unittest discover tests`.
- Covered test modules:
  - `test_api_routes.py`: REST endpoint verification.
  - `test_code_creation.py`: Agent execution and streaming behavior.
  - `test_github_service.py`: Git operations and token parsing.
  - `test_intent_service.py`: Classification of user prompts.
  - `test_project_service.py`: Workspace scanning and cleanup.
  - `test_prompt_service.py`: `prompt.txt` manipulation.
  - `test_server.py`: FastAPI application startup and CORS verification.

## 12. Deployment
- **Target Platform**: Google Cloud Run (Fully managed serverless).
- **Target Project**: `ai-learning-499409`.
- **Region**: `us-central1`.
- **Production Service Name**: `remote-code-agent`.
- **Production Backend URL**: `https://remote-code-agent-289332143182.us-central1.run.app`.
- **Staging Service Name**: `remote-code-agent-staging`.
- **Frontend Hosting**: Vercel (`https://remote-code-agent-ui.vercel.app`), configured with `VITE_API_URL=https://remote-code-agent-289332143182.us-central1.run.app`.
- **Container Build**: Docker build from root `Dockerfile` using Python 3.11-slim, installing Git, GitHub CLI, and dependencies.
- **Port**: Container listens on port `8080`.
- **Access**: Unauthenticated invocations enabled (`--allow-unauthenticated`).
- **CI/CD Workflow**:
  - Pull requests trigger `.github/workflows/pr-staging.yml` (tests + staging deployment).
  - Merges to `main` trigger `.github/workflows/deploy-prod.yml` (tests + production deployment).
