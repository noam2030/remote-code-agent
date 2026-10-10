# Project Specification

## 1. Overview
Remote Code Agent is an autonomous AI-driven code generation, modification, and execution engine operating as **Antigravity CLI on Cloud**, built with the Google Antigravity SDK and FastAPI, paired with a modern React/TypeScript dashboard.

As a core application feature, the web interface loads and catalogues all repositories belonging to the authenticated user's GitHub account (`<owner>/*`) alongside local projects. The user selects which repository to work on, or creates a new project repository, or deletes one. Once the user selects a repository and instructs the agent to write new code or update existing code, the application clones the selected repository into `workspace/<project_name>` (or pulls latest changes if already present), implements the requested code changes via Antigravity CLI on Cloud, and commits and pushes the updated code directly to the dedicated GitHub repository (`<owner>/<project_name>`). If asked to deploy, the agent adds GitHub Actions workflows targeting Google Cloud project `ai-learning` (`ai-learning-499409`) and Vercel scope `noam-projects2`.

The service is deployed on Google Cloud Run under project `ai-learning-499409`.

## 2. Requirements
- **Application-Level Repository Management**: The webpage automatically loads all user GitHub repositories on startup via `GET /api/projects`. Users can select any repository to work on, create a new repository, or delete an existing one directly in the UI.
- **Repository Cloning & Synchronization**: When a user selects a repository and submits an instruction to write new code or update code:
  - If the project has not yet been cloned locally, the application automatically clones the repository into `workspace/<project_name>`.
  - If the project already exists locally in `workspace/<project_name>`, the application pulls latest remote changes to ensure the workspace is up to date before code generation begins.
- **Antigravity CLI on Cloud Code Generation**: Implements requested code additions or updates directly inside the project workspace directory `workspace/<project_name>`, running tests and maintaining code quality.
- **Dedicated GitHub Push**: Commits and pushes generated or modified code directly to the user's dedicated GitHub repository (`<owner>/<project_name>`) on the `main` branch.
- **Automated Deployment Workflows**: When asked to deploy, generate GitHub Actions workflows (`.github/workflows/deploy.yml`):
  - Google Cloud Platform deployments target project `ai-learning` (`ai-learning-499409`) on Cloud Run.
  - Vercel deployments target scope/team `noam-projects2`.
- **Cloud Persistence**: Persistent application state uses Google Cloud Firestore in project `ai-learning-499409` under dedicated collections, with mock/in-memory fallbacks for offline testing.
- **Real-Time Streaming**: Stream logs, tool invocations, and agent actions to client applications using Server-Sent Events (SSE).
- **Project Isolation**: Maintain independent workspace directories under `workspace/<project_name>` for each generated or managed project.
- **Prompt History Tracking**: Persist sequential user prompts per project in `prompt.txt` (`1. <prompt>`, `2. <prompt>`).
- **Read-Only / Retrieval Mode**: Support query-only intent detection to inspect repository files without altering code or pushing unwanted commits.
- **Continuous Integration & Delivery**: Maintain GitHub Actions workflows for automated test execution, staging deployment on PRs, and production deployment on merge to `main`.

## 3. User Experience
- **Interactive Dashboard & Repository Navigator**:
  - The sidebar automatically loads all user GitHub repositories on page load.
  - Users can browse, search, and click any repository to make it active for inspection or modification.
  - Controls to create a new project (`+ New`) or delete a project (`🗑️`).
- **Target Project Banner & File Explorer**:
  - Displays the active project name, direct GitHub link, lines of code, and file count.
  - On-demand file explorer drawer allows opening and inspecting source files and master prompt history (`prompt.txt`).
- **Terminal & Log Viewer**: Real-time console view rendering color-coded output from backend SSE streams during code generation, testing, and GitHub pushing.
- **Execution Controls**: Prompt input with quick actions to initiate generation, inspect architecture, or cancel in-progress operations.

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
     │    ├── Code Creation (Antigravity SDK Runner & Streamer)
     │    ├── Intent Detection (Info vs Code)
     │    ├── Project Service (Workspace, GitHub Repo Catalog & Sync)
     │    ├── Prompt Service (prompt.txt History)
     │    └── GitHub Service (Repo Discovery, Clone, Init & Push)
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
- `services/code_creation.py`: Core agent execution loop utilizing `google.antigravity` configured as Antigravity CLI on Cloud. Ensures target repository is cloned into `workspace/<project_name>` (and pulled up to date), executes agent in workspace, streams tool calls and logs, and pushes resulting commits directly to the dedicated GitHub repository.
- `services/intent_service.py`: Classifies user input into code modification tasks or informational queries.
- `services/project_service.py`: Discovers all user GitHub repositories via `gh repo list` and REST API, merges with local workspace projects, syncs dedicated repositories on demand, and calculates stats.
- `services/prompt_service.py`: Parsing, updating, and synthesizing project prompt history in `prompt.txt`.
- `services/github_service.py`: Dedicated project repository creation (`<owner>/<project_name>`), repository discovery, remote git publishing directly to `main`, and authenticated remote URL generation.
- `server.py`: FastAPI application factory with CORS middleware and error handling.

## 7. Frontend
The frontend is structured under `frontend/`:
- `src/components/`: Reusable UI modules including `Header`, `Sidebar`, `TargetProjectBanner`, `FilesDrawer`, `TerminalStream`, `PromptEditor`, and modal dialogs.
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
- **Project Schema**:
  ```typescript
  export interface Project {
    name: string
    description?: string
    github_url: string
    cloud_run_url: string | null
    has_remote: boolean
    is_local: boolean
    is_private?: boolean
    files: string[]
    files_count: number
    files_detail: ProjectFileDetail[]
    lines_of_code: number
    tokens_spent: number
    stats: ProjectStats
  }
  ```
- **SSE Event Protocol**:
  - `data: {"type": "log", "message": "..."}`
  - `data: {"type": "tool_call", "tool": "..."}`
  - `data: {"type": "error", "error": "..."}`
  - `data: {"type": "done", "project": "...", "repo_url": "..."}`

## 9. API
- `GET /api/health`: Health status endpoint returning status code 200 and system health metadata.
- `GET /api/projects`: List all user GitHub repositories and local workspace projects.
- `GET /api/projects/{project_name}`: Retrieve project details, file list, stats, and README (syncing/cloning from GitHub into `workspace/<project_name>` if needed).
- `DELETE /api/projects/{name}`: Delete project workspace directory and optionally remove remote GitHub repository.
- `GET /api/projects/{name}/files/{file_path}`: Retrieve content and metadata for a specific file in a project.
- `POST /api/generate`: Initiate code generation or prompt execution on the target project, ensuring it is cloned and pulled up to date, returning an SSE stream, and pushing commits to GitHub.
- `GET /api/projects/{name}/prompts`: Retrieve history of prompts for the specified project.

## 10. Configuration
The application relies on the following environment variables:
- `GEMINI_API_KEY`: API key for Gemini models and Google Antigravity SDK.
- `GH_TOKEN` / `GITHUB_TOKEN`: GitHub personal access token with `repo` scope for repository management.
- `AGENT_WORKSPACE`: Relative or absolute path to the local project workspace (default: `workspace`).
- `GITHUB_OUTPUT_REPO`: Default GitHub repository name for central output catalog.
- `GCP_OUTPUT_PROJECT_ID`: Target Google Cloud Project ID (`ai-learning-499409`).
- `VERCEL_SCOPE`: Target Vercel team/scope for deployments (`noam-projects2`).
- `VERCEL_TOKEN`: Vercel personal access token for automated frontend CI/CD deployments.
- `VERCEL_ORG_ID`: Vercel Team ID (`team_abCCfq6oAKpFKOLdLU0hsGg5`).
- `VERCEL_PROJECT_ID`: Vercel Project ID (`prj_haBy0oc6TegmML9Z7aj7yKlMFgxm`).
- `PORT`: HTTP port for backend server (default: `8080`).
- `CORS_ORIGINS`: Comma-separated list of allowed origins.
- `FRONTEND_URL`: URL of the deployed frontend application (`https://remote-code-agent-ui.vercel.app`).
- `VITE_API_URL`: Frontend environment variable defining the backend API URL (production: `https://remote-code-agent-289332143182.us-central1.run.app`).

## 11. Testing
- Automated unit and integration tests are placed in `backend/tests/`.
- Test execution command: `.venv/bin/python -m unittest discover tests`.
- Frontend build validation: `npm run build` executed in `frontend/`.
- Covered test modules:
  - `test_api_routes.py`: REST endpoint verification.
  - `test_code_creation.py`: Agent execution, repository clone/pull, streaming behavior, and dedicated GitHub pushing.
  - `test_github_service.py`: Git operations, token parsing, and user repo discovery.
  - `test_intent_service.py`: Classification of user prompts.
  - `test_project_service.py`: GitHub repository catalog discovery, workspace scanning, dedicated repo sync, and cleanup.
  - `test_prompt_service.py`: `prompt.txt` manipulation.
  - `test_server.py`: FastAPI application startup and CORS verification.
  - `test_ci_workflows.py`: Verification of CI/CD workflow definitions, trigger configurations, and security secret requirements.

## 12. Deployment
- **Target Backend Platform**: Google Cloud Run (Fully managed serverless).
- **Target Project**: `ai-learning-499409`.
- **Region**: `us-central1`.
- **Production Backend Service Name**: `remote-code-agent`.
- **Production Backend URL**: `https://remote-code-agent-289332143182.us-central1.run.app`.
- **Staging Backend Service Name**: `remote-code-agent-staging`.
- **Frontend Target Platform**: Vercel (`https://remote-code-agent-ui.vercel.app`), configured with `VITE_API_URL=https://remote-code-agent-289332143182.us-central1.run.app`.
- **Container Build**: Docker build from root `Dockerfile` using Python 3.11-slim, installing Git, GitHub CLI, and dependencies.
- **Port**: Container listens on port `8080`.
- **Access**: Unauthenticated invocations enabled (`--allow-unauthenticated`).
- **CI/CD Architecture**:
  - **Pull Request Verification (`.github/workflows/pr-verify.yml`)**:
    - Triggered on pull requests targeting `main`.
    - Runs backend unit test suite and frontend build verification.
    - Does NOT automatically deploy to staging.
  - **Optional On-Demand Staging Deployment (`.github/workflows/deploy-staging.yml`)**:
    - Triggered manually on demand via GitHub Actions UI (`workflow_dispatch`).
    - Deploys the API to Google Cloud Run staging (`remote-code-agent-staging`).
    - Deploys the Frontend to Vercel preview/staging if `VERCEL_TOKEN` is configured.
  - **Production Deployment (`.github/workflows/deploy-prod.yml`)**:
    - Triggered automatically on push / merge to `main`.
    - Runs backend automated tests and frontend build validation.
    - Deploys backend API to Google Cloud Run production (`remote-code-agent`).
    - Deploys frontend UI to Vercel production (`--prod`) targeting the project scope and setting `VITE_API_URL` to the production backend URL.

