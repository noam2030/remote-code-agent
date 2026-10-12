# Project Specification

## 1. Overview
Remote Code Agent is an autonomous AI-driven code generation, modification, and execution engine operating as **Antigravity CLI on Cloud**, built with the Google Antigravity SDK and FastAPI, paired with a modern React/TypeScript dashboard.

As a core application feature, the web interface loads and catalogues all repositories belonging to the authenticated user's GitHub account (`<owner>/*`). The project catalog is a strict, dynamic reflection of the user's GitHub repositories, presented in the same order as on GitHub with the most recently used/updated repository appearing first; it does not list internal subdirectories of repositories (such as `frontend` or `backend`) and does not store or persist projects in any database or persistent storage. The user selects which repository to work on or creates a new project repository. Project and repository deletion is completely disabled across the system to protect repositories and local workspaces from accidental data loss. Once the user selects a repository and instructs the agent to write new code or update existing code, the application clones the selected repository into `workspace/<project_name>` (or pulls latest changes if already present), implements the requested code changes via Antigravity CLI on Cloud, and commits and pushes the updated code directly to the dedicated GitHub repository (`<owner>/<project_name>`). If asked to deploy, the agent adds GitHub Actions workflows targeting Google Cloud project `ai-learning` (`ai-learning-499409`) and Vercel scope `noam-projects2`.

The system supports seamless cross-device session continuation: code generation is managed server-side via a decoupled `RunManager` background task so users can initiate a prompt from a desktop browser (e.g. Mac), close the browser, and subsequently open the application on a mobile phone browser to monitor real-time progress, inspect replayed logs, and continue submitting follow-up prompts from the phone.

The agent strictly adheres to two core operational skills across every managed project: **`project-specification`** (maintaining a single, authoritative `SPEC.md` containing all 12 mandatory sections: Overview, Requirements, User Experience, Architecture, Technology Stack, Backend, Frontend, Data Model, API, Configuration, Testing, Deployment) and **`development-workflow`** (updating `SPEC.md` first before implementing changes, ensuring code is an exact reflection of `SPEC.md`, maintaining sequentially numbered prompt history in `prompt.txt`, ensuring comprehensive automated tests in `tests/`, and configuring CI/CD deployment workflows). The agent's prompts and skills are maintained in dedicated, human-readable files under the services documentation directory (`backend/src/remote_code_agent/services/docs/prompt.md` and `backend/src/remote_code_agent/services/docs/skills/`), completely unified within the services directory and decoupled from Python code for simplified inspection, editing, and maintenance.

The service is deployed on Google Cloud Run under project `ai-learning-499409`.

## 2. Requirements
- **Dedicated Prompt and Skills Architecture**: The agent's system prompt and operational skills are completely separated from backend runtime execution logic and organized in dedicated Markdown documents inside the services package directory (`backend/src/remote_code_agent/services/docs/`): `backend/src/remote_code_agent/services/docs/prompt.md` for the core system prompts and chat prompts, and individual skill files inside `backend/src/remote_code_agent/services/docs/skills/` (`backend/src/remote_code_agent/services/docs/skills/project-specification.md` and `backend/src/remote_code_agent/services/docs/skills/development-workflow.md`). Prompts and skills must be easily readable and maintainable without touching Python code files, and code generation services contain zero embedded prompt strings.
- **Application-Level Repository Management**: The webpage automatically loads all user GitHub repositories on startup via `GET /api/projects` in the exact order as GitHub (most recently updated/used repository appearing first). The project list is a dynamic reflection of GitHub repositories. Subdirectories of repositories (e.g., `frontend` or `backend`) are never listed as projects, and projects are never stored to persistent database stores. Users can select any repository to work on or create a new repository. Project and repository deletion is completely removed to protect codebase assets from accidental deletion.
- **Repository Cloning & Synchronization**: When a user selects a repository and submits an instruction to write new code or update code:
  - If the project has not yet been cloned locally, the application automatically clones the repository into `workspace/<project_name>`.
  - If the project already exists locally in `workspace/<project_name>`, the application pulls latest remote changes to ensure the workspace is up to date before code generation begins.
- **Antigravity CLI on Cloud Code Generation**: Implements requested code additions or updates directly inside the project workspace directory `workspace/<project_name>`, running tests and maintaining code quality.
- **Decoupled Background Execution & Cross-Device Session Handoff**: Code generation tasks execute in independent server-side background tasks managed by a singleton `RunManager`, decoupled from individual client HTTP connection lifetimes. Closing a client browser tab or socket does not cancel generation.
- **Re-attachable Active Run & Live Stream Replay**: The server provides an active run status endpoint (`GET /api/runs/active`) and an active run stream endpoint (`GET /api/runs/active/stream`). Clients opening the application on any device (e.g. mobile phone) can query active run status, auto-select the running project, replay existing log history, and attach to live SSE streaming.
- **Heartbeat-Backed Unbuffered SSE Streaming**: Active stream endpoints yield an immediate connection header and periodic keep-alive heartbeat comments (`: keepalive\n\n`) every 5 seconds during idle periods between generator chunks, preventing Google Cloud Run proxies, cellular carrier gateways, and iOS Safari from buffering or hanging quiet streams.
- **Cross-Device Mobile Continuation & Unstuck Resilience**: When accessing the application from a mobile browser, users can monitor in-progress runs, view logs, and immediately submit follow-up prompts from their mobile device. The frontend maintains an active run polling synchronization loop every 3 seconds as a resilient fallback, ensuring the UI catches up on logs, detects completion, and clears generation locks even if mobile network connectivity pauses or the device sleeps.
- **Mobile Responsive Layout & View Switching**: Responsive adaptations on viewports under 768px providing a dedicated mobile view toggle (`⚡ Live Console` / `📁 Projects`). Rather than awkwardly stacking the sidebar on top of the console and pushing the terminal off-screen, mobile users can switch directly between the live generation console and the project catalog.
- **Dedicated GitHub Push**: Commits and pushes generated or modified code directly to the user's dedicated GitHub repository (`<owner>/<project_name>`) on the `main` branch.
- **Automated Deployment Workflows & Naming Conventions**: When asked to deploy, generate GitHub Actions workflows (`.github/workflows/deploy.yml`):
  - **Backend Cloud Run Deployment**: Backend services MUST be named `<project_name>-api` (e.g., `hello-api`, `hello-1-api`). Deploys applications to Google Cloud project `ai-learning` (`ai-learning-499409`) on Cloud Run in region `us-central1` with unauthenticated access using secrets.GCP_SA_KEY. All Cloud Run deployments MUST use **Source type** (`gcloud run deploy <project_name>-api --source . ...`), building directly from source via Google Cloud Build. Workflows must NEVER use `docker build`, `docker push`, or `--image` flags. In Google Cloud Run, the environment variable `PORT` is reserved and injected automatically by the platform; workflows must NEVER define or pass `PORT` in `--set-env-vars` or `--update-env-vars`. Container listening port is configured exclusively via the `--port 8080` flag.
  - **Frontend Vercel Deployment**: Frontend UI web applications MUST be deployed to Vercel project `<project_name>-ui` (e.g., `hello-ui`, `hello-1-ui`) under team/scope `noam-projects2` using secrets.VERCEL_TOKEN.
- **Stateless Project Catalog & App Persistence**: The project catalog itself is stateless and dynamically retrieved directly from GitHub without persistent caching or storing projects in any database. For generated applications requiring database persistence, applications use Google Cloud Firestore in project `ai-learning-499409` under dedicated collections, with mock/in-memory fallbacks for offline testing.
- **Real-Time Streaming**: Stream logs, tool invocations, and agent actions to client applications using Server-Sent Events (SSE).
- **Project Isolation**: Maintain independent workspace directories under `workspace/<project_name>` for each generated or managed project.
- **Authoritative Project Specification (`SPEC.md`)**: For every generated or managed project, create and maintain a single, authoritative `SPEC.md` capturing the complete, current state of the application containing all mandatory sections 1 to 12 (1. Overview, 2. Requirements, 3. User Experience, 4. Architecture, 5. Technology Stack, 6. Backend, 7. Frontend, 8. Data Model, 9. API, 10. Configuration, 11. Testing, 12. Deployment). No section 1 to 12 may be omitted so another coding agent can recreate the project from scratch without the original conversation.
- **Spec-First Development Workflow**: Upon receiving any instruction to build, update, or modify an application, the agent must update `SPEC.md` first. Code, tests, and configuration must always be an exact reflection of `SPEC.md`, never deviating from or contradicting the specification.
- **Prompt History Tracking**: Persist sequential user prompts per project in `prompt.txt` (`1. <prompt>`, `2. <prompt>`).
- **Read-Only / Retrieval Mode**: Support query-only intent detection to inspect repository files without altering code or pushing unwanted commits.
- **Continuous Integration & Delivery**: Maintain GitHub Actions workflows for automated test execution, staging deployment on PRs, and production deployment on merge to `main`.

## 3. User Experience
- **Interactive Dashboard & Repository Navigator**:
  - The sidebar automatically loads all user GitHub repositories on page load.
  - Users can browse, search, and click any repository to make it active for inspection or modification.
  - Controls to create a new project (`+ New`). Project deletion is entirely removed.
  - Creating a new project (`+ New`) immediately adds the project to the top of the sidebar list with a `✨ New` indicator and selects it as the active target project, so it remains selected for code generation.
  - Selection state is case-insensitive and preserves canonical repository casing, ensuring that mixed-case or TitleCase projects (such as `OpenTrain` or `QR-X-Ray`) remain permanently active when selected.
- **Cross-Device Handover & Continuous Streaming**:
  - A user can enter a prompt on desktop (Mac), trigger generation, and close the browser or shut down their machine.
  - Opening the web application on a mobile phone (or any secondary browser) checks for active runs. If an active run is detected, the frontend automatically selects the relevant project, restores prior log output, displays an active generation indicator, and connects to the live stream to render ongoing progress in real-time.
  - When the process completes, the terminal stream displays the final output, and the prompt input is fully enabled so the user can immediately continue prompting directly from their phone.
- **Mobile Responsive Layout & View Switching (`⚡ Live Console` / `📁 Projects`)**:
  - On mobile screens (viewports under 768px), the layout provides a dedicated mobile view toggle at the top (`⚡ Live Console` and `📁 Projects`).
  - When viewing the console, the view focuses immediately and cleanly on the **Prompt Editor** and **Live Terminal Stream**, removing any redundant top project details banner to maximize visible console height on mobile.
  - Tapping `📁 Projects` displays the comprehensive project list and search box; selecting a repository switches back to the Console view with the selected project ready for generation.
  - The project list scroll container is strictly constrained to the remaining dynamic viewport height (`100dvh`), utilizing native momentum scrolling (`-webkit-overflow-scrolling: touch; touch-action: pan-y;`) and generous safe-area bottom padding (`calc(5rem + env(safe-area-inset-bottom, 2rem))`) to prevent touch event lockups, container freezing, or clipping of bottom cards behind mobile browser navigation bars.
  - Terminal output and prompt editor are optimized for touch interaction with full-width action buttons and readable mobile monospace sizing.
- **Comprehensive Project Cards & File Explorer**:
  - All project details, links, and drawer actions are consolidated directly within each project card in the sidebar:
    - Repository name, description, and active selection indicator.
    - Deployment and repository links: `🌐 UI` (Vercel Live URL), `🚀 API` (Cloud Run API URL), and `🐙 GitHub`.
    - Project statistics: Lines of Code (LOC), Tokens Spent, and File Count.
    - Drawer and modal actions: Direct action to toggle the project files drawer and direct action to view the master prompt (`prompt.txt`).
  - On-demand file explorer drawer allows opening and inspecting source files and master prompt history (`prompt.txt`).
- **Terminal & Log Viewer**: Real-time console view rendering color-coded output from backend SSE streams during code generation, testing, and GitHub pushing. Supports replaying buffered logs for newly attached clients.
- **Execution Controls & Streamlined Prompt Editor**: Prompt input with streamlined suggestion chips (`🎨 Modernize UI`, `🚀 Deploy Workflows`). Redundant header text (`Antigravity CLI on Cloud`) and target notice tag are removed from the generator card to provide a clean, uncluttered interface, with the target repository confirmed in the footer above the Generate button.
- **Fixed Viewport & Independent Pane Scrolling**:
  - The application desktop and mobile layouts adapt dynamically to viewport height (`100vh` and `100dvh`) with zero document-level page overflow.
  - The left sidebar fills the viewport height below the header with its header and search input fixed in place, while only the project items list (`.project-list`) scrolls vertically with native touch scrolling and ample bottom padding.
  - The right content area is fixed to the screen height (`overflow: hidden`). The prompt input sits at the top, while the terminal panel flexes to consume the remaining height, with only the terminal output log area scrolling vertically.

## 4. Architecture
The system consists of two primary tiers:
1. **Frontend**: Single-page application built with React 18, TypeScript, and Vite, deployed to Vercel.
2. **Backend**: Containerized FastAPI service running on Google Cloud Run, communicating with the Google Antigravity SDK and GitHub APIs.

```text
[ React / Vite Frontend (Vercel) ]
             │
             │ HTTPS / SSE (Active Run Re-attachment)
             ▼
[ FastAPI Backend (Google Cloud Run in ai-learning-499409) ]
     ├── Core Configuration (Env, Secrets, Paths)
     ├── API Layer (REST & SSE Endpoints)
     ├── Prompts & Skills Layer (backend/src/remote_code_agent/services/docs/prompt.md, backend/src/remote_code_agent/services/docs/skills/project-specification.md, backend/src/remote_code_agent/services/docs/skills/development-workflow.md)
     ├── Services
     │    ├── Agent Prompts Service (Dynamic Prompt & Skills Loader)
     │    ├── Run Manager (Decoupled Background Tasks, Log Buffering & Multi-Client Broadcast)
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
- `api/routes.py`: FastAPI routes registering `/api/health`, `/api/projects`, `/api/generate`, `/api/runs/active`, `/api/runs/active/stream`, and file inspection endpoints.
- `services/agent_prompts.py`: Dedicated lightweight file-loader service with zero hardcoded prompt or skill text. All prompts and skills reside exclusively inside the services documentation directory (`backend/src/remote_code_agent/services/docs/prompt.md` and `backend/src/remote_code_agent/services/docs/skills/*.md`). The service dynamically reads the markdown documents, injects skill contents into the `{skills}` placeholder, and performs parameter interpolation (`{target_name}`, `{app_name}`) at runtime for both agent system instructions and chat prompt messages.
- `services/run_manager.py`: Centralized singleton manager governing code generation background tasks. Decouples task execution from single client connections using `asyncio.create_task`, accumulates all streamed chunks into a memory buffer, and broadcasts live chunks to multiple client subscription queues simultaneously. Enables clients connecting after a task has started (e.g., from mobile) to retrieve active state via `get_active_run()` and stream past logs plus live updates via `stream_run()`. Yields an initial connection flush and periodic SSE keep-alive heartbeat comments (`: keepalive\n\n`) every 5 seconds to prevent mobile browsers, carrier networks, and Cloud Run proxies from buffering or stalling quiet streams.
- `services/code_creation.py`: Core agent execution loop utilizing `google.antigravity`. Ensures target workspace directory exists, and consumes system instructions and chat prompts exclusively from `services/agent_prompts.py` (which loads `backend/src/remote_code_agent/services/docs/prompt.md` and `backend/src/remote_code_agent/services/docs/skills/`), containing zero inline prompt strings. Directs the agent to strictly follow the `development-workflow` and `project-specification` skills across every managed project. Mandates maintaining a single authoritative `SPEC.md` containing all mandatory sections 1 to 12 (Overview, Requirements, User Experience, Architecture, Technology Stack, Backend, Frontend, Data Model, API, Configuration, Testing, Deployment), updating `SPEC.md` first before writing code, and ensuring code is an exact reflection of `SPEC.md`. Enforces standard deployment naming conventions: backend Cloud Run service `<project_name>-api` and frontend Vercel project `<project_name>-ui`. Enforces valid GitHub Actions syntax in generated workflows, utilizing standard event/branch job-level conditionals (`if: github.event_name == 'push' && github.ref == 'refs/heads/main'`) and never using the `secrets` context in job-level `if:` expressions. Strictly instructs the agent that Google Cloud Run deployments MUST be configured with **Source type** (`--source .`) rather than Container type (`docker build`, `docker push`, `--image`). Strictly instructs the agent that Google Cloud Run reserves `PORT`, prohibiting setting or passing `PORT` in `--set-env-vars` or `--update-env-vars` when generating `gcloud run deploy` commands, and requiring container port configuration to use `--port 8080` instead. The agent does not create virtual environments (`.venv`), install dependencies, or run git commands. Once code generation finishes, the backend service automatically commits and pushes all created files to GitHub.
- `services/intent_service.py`: Classifies user input into code creation/modification tasks or informational queries.
- `services/project_service.py`: Discovers user GitHub repositories via `gh repo list` and REST API as a direct, dynamic reflection of GitHub without inspecting subdirectories or synthesizing dummy projects for internal folders such as `frontend` or `backend`. Formats and sorts repository catalog records in descending order of `updated_at` (most recently used/updated repository appearing first), matching GitHub's default repository order. Does not store projects in any persistent storage or database. Local workspace directories under `workspace/` serve strictly as ephemeral working directories for cloned repositories. Preserves the user's project name and casing, and calculates repository statistics. Resolves live deployment links for both backend API (`cloud_run_url` targeting `<project_name>-api`) and frontend UI (`vercel_url` targeting `<project_name>-ui`). Project and repository deletion is entirely removed from the application to protect codebase assets from accidental deletion.
- `services/prompt_service.py`: Parsing, updating, and synthesizing project prompt history in `prompt.txt` with fast fallback, consuming synthesis prompts from `services/agent_prompts.py`.
- `services/github_service.py`: Automates dedicated GitHub repository creation (`<owner>/<project_name>`), initializes git, writes `.gitignore`, commits generated files, and executes deterministic git pushes directly to `main` of the dedicated repository without mutating or deleting repository files. Automatically provisions deployment secrets (`GCP_SA_KEY`, `VERCEL_TOKEN`) from the backend environment to target repositories via `gh secret set`, enabling generated CI/CD workflows to execute out-of-the-box. Requires a `GH_TOKEN` configured with `repo` and `workflow` scopes, surfacing clear diagnostics if permission errors occur.
- `server.py`: FastAPI application factory with CORS middleware and error handling.

## 7. Frontend
The frontend is structured under `frontend/`:
- `src/components/`: Reusable UI modules including `Header`, `Sidebar` (hosting complete project details, stats, deployment links, and direct file/prompt drawer actions), `FilesDrawer`, `TerminalStream`, `PromptEditor` (clean prompt input with focused suggestion chips `🎨 Modernize UI` and `🚀 Deploy Workflows`, streamlined without redundant header banner or target tag), and modal dialogs.
- `src/services/api.ts`: Typed HTTP client wrapping backend REST endpoints, active run retrieval (`getActiveRun`), and streaming endpoints (`streamActiveRun`, `generateCodeStream`).
- `src/types/`: Interfaces for projects, generation events, active runs, file trees, and system status.
- `src/App.tsx`: Top-level application state orchestrator, handling project creation persistence, active project selection with case-insensitivity, active run auto-detection and re-connection on mount, seamless mobile handover, mobile view switching (`⚡ Live Console` / `📁 Projects`), streamlined console area without top banner, non-blocking stream lifecycle with background poll fallback, and code generation streaming.
- `src/index.css`: Global styles, dynamic viewport height sizing (`100vh` and `100dvh`), flex-constrained independent scrolling containers, mobile navigation tab styles, touch-friendly scroll physics (`touch-action: pan-y; -webkit-overflow-scrolling: touch`), and safe-area bottom padding ensuring the full project catalog scrolls smoothly to the last item on mobile without lockups.
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
    vercel_url?: string | null
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
- **Active Run Schema**:
  ```typescript
  export interface ActiveRunResponse {
    active: boolean
    run_id: string | null
    project_name: string | null
    prompt: string | null
    status: 'idle' | 'running' | 'completed' | 'error'
    logs: string
    started_at: number | null
  }
  ```

## 9. API
- `GET /api/health`: Health status endpoint returning status code 200 and system health metadata.
- `GET /api/projects`: List all user GitHub repositories dynamically as a direct reflection of GitHub.
- `GET /api/projects/{project_name}`: Retrieve project details, file list, stats, and README (syncing/cloning from GitHub into `workspace/<project_name>` if needed).
- `GET /api/projects/{name}/files/{file_path}`: Retrieve content and metadata for a specific file in a project.
- `GET /api/runs/active`: Query current active or latest run status, returning `ActiveRunResponse` with accumulated logs.
- `GET /api/runs/active/stream`: Stream ongoing run output (replays buffered history then streams live events) over text/plain or SSE.
- `POST /api/generate`: Initiate code generation or prompt execution on the target project, ensuring it is cloned and pulled up to date, running via background `RunManager`, returning a live stream, and pushing commits to GitHub.
- `GET /api/generate`: GET variant of code generation streaming endpoint.
- `GET /api/projects/{name}/prompts`: Retrieve history of prompts for the specified project.

## 10. Configuration
The application relies on the following environment variables:
- `GEMINI_API_KEY`: API key for Gemini models and Google Antigravity SDK.
- `GH_TOKEN` / `GITHUB_TOKEN`: GitHub personal access token or OAuth token with `repo` and `workflow` scopes for repository and workflow management.
- `AGENT_WORKSPACE`: Relative or absolute path to the local project workspace (default: `workspace`).
- `AGENT_DOCS_DIR`: Optional custom path to the documentation folder containing `prompt.md` and `skills/` (default: auto-detected `backend/src/remote_code_agent/services/docs/`).
- `GITHUB_TARGET_OWNER`: GitHub username / organization owning generated repositories (defaults dynamically to authenticated GitHub user or `noam2030`).
- `GCP_OUTPUT_PROJECT_ID`: Target Google Cloud Project ID (`ai-learning-499409`).
- `GCP_SA_KEY`: Service account credentials JSON for Google Cloud deployments, automatically provisioned to generated repositories to enable Cloud Run deployments.
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
  - `test_agent_prompts.py`: Verification of dynamic prompt loading from `backend/src/remote_code_agent/services/docs/prompt.md` and individual skill documents in `backend/src/remote_code_agent/services/docs/skills/`, template parameter interpolation, and robust fallback behavior.
  - `test_api_routes.py`: REST endpoint verification (including `/api/runs/active` and `/api/runs/active/stream`).
  - `test_run_manager.py`: Background task orchestration, multi-subscriber queues, buffered log replaying, and state retention.
  - `test_code_creation.py`: Agent execution, repository clone/pull, streaming behavior, and dedicated GitHub pushing.
  - `test_github_service.py`: Git operations, token parsing, and user repo discovery.
  - `test_intent_service.py`: Classification of user prompts.
  - `test_project_service.py`: GitHub repository catalog discovery, most-recently-updated ordering matching GitHub, workspace scanning, dedicated repo sync, and cleanup.
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
- **Container Build**: Docker build from root `Dockerfile` using Python 3.11-slim, installing Git, GitHub CLI, and dependencies. The `COPY backend/ .` layer bundles the entire backend including `backend/src/remote_code_agent/services/docs/` into `/app/src/remote_code_agent/services/docs/` automatically.
- **Port**: Container listens on port `8080`.
- **Request Timeout**: Configured with `--timeout=3600` (up to 60 minutes) to support multi-step agent code generation and build processes without premature HTTP connection drops.
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

