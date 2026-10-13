# Project Specification

## 1. Overview
Remote Code Agent is an autonomous AI-driven code generation, modification, and execution engine where the actual remote code agent is the **`agy` CLI pre-installed in Docker**. The backend service, built with FastAPI, runs in a containerized environment on Google Cloud Run paired with a modern React/TypeScript dashboard.

When a user writes a prompt in the web UI, the web application calls the pre-installed `agy` CLI binary (`/usr/local/bin/agy` or `$PATH`) with this prompt non-interactively:
```bash
agy -p "<prompt>" --dangerously-skip-permissions
```
The execution runs in the active project's workspace directory (`workspace/<project_name>`). Only when the CLI process completely finishes execution does the web application return the complete response to the user.

As a core application feature, the web interface loads and catalogues all repositories belonging to the authenticated user's GitHub account (`<owner>/*`). The project catalog is a strict, dynamic reflection of the user's GitHub repositories, presented in the same order as on GitHub with the most recently used/updated repository appearing first; it does not list internal subdirectories of repositories (such as `frontend` or `backend`) and does not store or persist projects in any database or persistent storage. The user selects which repository to work on or creates a new project repository. Project and repository deletion is completely disabled across the system to protect repositories and local workspaces from accidental data loss.

The system supports seamless cross-device session continuation: code generation is managed server-side via a decoupled `RunManager` background task. Users can submit a prompt from a desktop browser (e.g. Mac), close the browser, and subsequently open the application on a mobile phone browser; the phone detects the active run, displays the in-progress status, and when the `agy` CLI finishes on the server, the full response is delivered to the phone. If the CLI already finished before reconnecting, the full response is immediately replayed.

The `agy` CLI authenticates headlessly inside the Docker container using environment variables and automatic provider settings:
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`: API key credentials for Gemini models. When `GEMINI_API_KEY` is present, the backend automatically configures `~/.gemini/antigravity-cli/settings.json` with `"modelProvider": "gemini"`. This switches `agy` to connect directly to the Gemini API, completely bypassing OS Keyring and OAuth browser prompts for 100% headless remote execution.
- `AGY_OAUTH_TOKEN`: Optional injected Antigravity OAuth credentials (JSON content of `jetski-standalone-oauth-token`). The backend automatically writes this token to `~/.gemini/jetski-standalone-oauth-token` (with mode 0600) upon startup or prior to invoking `agy`.
- Google Cloud Application Default Credentials (ADC) / `GOOGLE_APPLICATION_CREDENTIALS` / `GCP_SA_KEY`: Native service account authentication on Cloud Run.
- `GH_TOKEN` / `GITHUB_TOKEN`: GitHub credentials for repository management, git operations, and pull requests via `gh`.

The service is packaged using a single, authoritative root `Dockerfile` and deployed on Google Cloud Run under project `ai-learning-499409`.

## 2. Requirements
- **Pre-installed `agy` CLI in Docker**: The container build installs the official Antigravity CLI flat binary (`agy`) via the official Unix installer (`curl -fsSL https://antigravity.google/cli/install.sh | bash -s -- -d /usr/local/bin`) directly into `/usr/local/bin/agy`, ensuring it is executable and immediately available on system `$PATH`.
- **Single Authoritative Dockerfile**: All container builds execute exclusively from the single root `Dockerfile` in the project repository root. Redundant nested Dockerfiles (e.g. `backend/Dockerfile`) are removed to prevent build ambiguity.
- **CLI Prompt Invocation & Session Continuity**: When the user submits a prompt in the web UI, the backend executes the `agy` CLI non-interactively inside the target project workspace (`workspace/<project_name>`). For subsequent prompts within an existing project workspace session, execution passes `--continue` to retain multi-turn conversational context, awareness of previously written code, and iterative instruction memory.
- **Unified Continuous Session Console**: All prompt interactions and outputs within a project session accumulate into a single continuous console transcript. The web interface and backend `RunManager` preserve cumulative logs across turns instead of wiping the console on each new command, allowing users to review the complete history of instructions and outputs.
- **Live Output Streaming & Execution Safety**: Subprocess execution in `execute_agy_cli` streams stdout and stderr asynchronously in real time directly to the client via non-blocking chunk reading (`reader.read(4096)`) rather than waiting for newlines or buffering until process termination. Standard input is closed via `stdin=asyncio.subprocess.DEVNULL` to prevent hangs on interactive prompts. Environment variables `GIT_TERMINAL_PROMPT=0`, `GH_PROMPT_DISABLED=1`, and `GIT_ASKPASS=/bin/echo` are enforced to prevent child git/gh tools from prompting on terminal devices. Processes are launched with `start_new_session=True` so process group termination cleanly cleans up child processes. Subprocess termination awaits `proc.wait()` first, followed by a strict 2.0s bounded grace period to drain stream pipes so background daemon processes (e.g. servers) never block execution. Execution timeout is set to 300s (with `--print-timeout 300s`).
- **Git Environment Parity with Local Mac**: In the container environment, `ensure_git_config(env)` configures `user.name`, `user.email`, `init.defaultBranch main`, and executes `gh auth setup-git` using `GH_TOKEN` prior to CLI execution. This guarantees that any git or gh command executed by `agy` in the project workspace (including `git commit`, `git push`, and `gh pr create`) automatically authenticates without interactive prompts, identical to a developer's local Mac CLI environment. All prompts execute directly through the `agy` CLI with `--continue` for complete multi-turn local-parity execution.
- **Run Cancellation & Subprocess Termination**: The system supports stopping in-flight generation runs at any time via `cancel_run()` and `POST /api/runs/cancel`. When triggered, the backend sends `SIGTERM` (and `SIGKILL` if ungraceful) to the child subprocess, updates run status to `cancelled`, logs `⏹️ [Run Cancelled] Generation was cancelled by user.`, and immediately frees the system to accept subsequent user prompts.
- **Space/Hyphen Normalized Project Intent Detection**: When the user references an existing workspace project in their prompt (e.g. "hello world app"), `detect_project_from_prompt` recognizes project names regardless of whether hyphens, underscores, or spaces are used, and automatically routes execution to the referenced project workspace.
- **Headless Container Authentication**: The backend configures `modelProvider: "gemini"` in `~/.gemini/antigravity-cli/settings.json` and forwards execution environment variables to the `agy` subprocess: `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GH_TOKEN`, `PATH`, and `HOME`. `agy` executes headlessly without prompting for interactive OAuth login URLs.
- **Decoupled Background Execution & Cross-Device Session Handoff**: Code generation tasks execute in independent server-side background tasks managed by a singleton `RunManager`, decoupled from individual client HTTP connection lifetimes. Closing a client browser tab or socket does not cancel generation.
- **Re-attachable Active Run**: The server provides `GET /api/runs/active`, `GET /api/runs/active/stream`, and `POST /api/runs/cancel`. Clients opening the application on any device query active run status. While `agy` runs, the status is `running`. Once finished, the status is `completed` (or `cancelled`/`error`) with the full cumulative session response.
- **Application-Level Repository Management**: The webpage automatically loads all user GitHub repositories on startup via `GET /api/projects` in the exact order as GitHub (most recently updated/used repository appearing first). Subdirectories are never listed as projects, and projects are never stored in databases.
- **Repository Cloning & Synchronization**: When a user selects a repository and submits an instruction to write new code or update code:
  - If the project has not yet been cloned locally, the application automatically clones the repository into `workspace/<project_name>`.
  - If the project already exists locally in `workspace/<project_name>`, the application pulls latest remote changes to ensure the workspace is up to date before `agy` executes.
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
- **Stop / Cancel Run Action**:
  - While code generation is running, the Prompt Editor and Terminal Stream surface an interactive `⏹️ Stop` action button.
  - Clicking Stop immediately triggers backend cancellation, terminates the running `agy` CLI process, appends a cancellation notice to the terminal log, and frees the prompt input so the user can immediately submit new requests without delay.
- **Live Real-Time Subprocess Streaming**:
  - The console receives and renders stdout and stderr lines from `agy` in real time as they happen, showing tool calls, planning steps, and command outputs without silent multi-minute delays.
- **Cross-Device Handover & Continuous Streaming**:
  - A user can enter a prompt on desktop (Mac), trigger generation, and close the browser or shut down their machine.
  - Opening the web application on a mobile phone (or any secondary browser) checks for active runs. If an active run is detected, the frontend automatically selects the relevant project, restores prior log output, displays an active generation indicator, and connects to the live stream to render ongoing progress in real-time.
  - When the process completes, the terminal stream displays the final output, and the prompt input is fully enabled so the user can immediately continue prompting directly from their phone.
- **Ongoing Stream Continuation & Unified Session UX**:
  - The live console maintains a continuous transcript across all user commands for the active project.
  - When the user submits a new prompt (such as "implement feature A", then "great, publish it"), the console does not wipe previous logs. It renders a clean user prompt divider (`💬 [User Prompt] <prompt>`) and streams the execution output seamlessly beneath the prior turns with automatic scrolling.
  - Reconnecting from another device or reloading the page automatically loads the full cumulative session transcript.
  - Users can manually clear the screen at any time via the dedicated "Clear" button in the terminal header.
- **Planning Phase UX**: When the agent yields its plan ending with `Confirm?`, the terminal stream displays the plan clearly. The Prompt Editor surfaces a quick `✅ Confirm Plan` chip to immediately submit confirmation.
- **Pull Request & Merge Approval UX**: When a feature branch is pushed and a PR is created, the terminal stream highlights the Pull Request URL. The UI surfaces a `🔀 Merge Pull Request` chip to approve and merge. Triggering merge appends `💬 [User] merge` and the merge/deployment logs directly to the same continuous console stream.
- **Prompt Editor Guidance**: The footer reflects the true pair-programming branch & PR lifecycle: changes are proposed, confirmed, implemented on dedicated feature branches, reviewed via PR, and merged upon approval.
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
- **Terminal & Log Viewer**: Real-time console view rendering color-coded output from backend SSE streams during code generation, testing, branching, pull request creation, and squash-merging. Supports replaying buffered logs for newly attached clients.
- **Loaded Skills Inspection & Viewer Modal**:
  - The application header navigation bar provides an interactive `🧠 Skills` action button indicating the count of dynamically loaded agent skills.
  - Clicking the button opens the `SkillsModal` dialog, allowing users to view and inspect all dynamically loaded skills (`development-workflow`, `project-specification`, etc.) without needing them stored locally in the project repository.
  - The modal provides tabbed switching across loaded skills, a copy action to copy the full markdown content to the clipboard, a direct link to the remote skills source repository on GitHub, and line-numbered formatting consistent with the application's code viewer modals.
- **Fixed Viewport & Independent Pane Scrolling**:
  - The application desktop and mobile layouts adapt dynamically to viewport height (`100vh` and `100dvh`) with zero document-level page overflow.
  - The left sidebar fills the viewport height below the header with its header and search input fixed in place, while only the project items list (`.project-list`) scrolls vertically with native touch scrolling and ample bottom padding.
  - The right content area is fixed to the screen height (`overflow: hidden`). The prompt input sits at the top, while the terminal panel flexes to consume the remaining height, with only the terminal output log area scrolling vertically.

## 4. Architecture
The system consists of two primary tiers:
1. **Frontend**: Single-page application built with React 18, TypeScript, and Vite, deployed to Vercel.
2. **Backend**: Containerized FastAPI service running on Google Cloud Run, invoking the pre-installed **`agy` CLI binary** in local project workspaces and interfacing with GitHub APIs.

```text
[ React / Vite Frontend (Vercel) ]
             │
             │ HTTPS / SSE (Active Run Re-attachment)
             ▼
[ FastAPI Backend (Google Cloud Run in ai-learning-499409) ]
     ├── Core Configuration (Env, Secrets, Paths, AGY_CLI_PATH)
     ├── API Layer (REST & SSE Endpoints, Lifespan Startup Handler)
     ├── Services
     │    ├── Run Manager (Decoupled Background Tasks, State Tracking, Cross-Device Reconnect)
     │    ├── Code Creation (Invokes pre-installed agy CLI subprocess, awaits completion)
     │    ├── Intent Detection (Info vs Plan vs Confirm vs Merge)
     │    ├── Project Service (Workspace, GitHub Repo Catalog & Sync)
     │    ├── Prompt Service (prompt.txt History)
     │    └── GitHub Service (Repo Discovery, Branches, PRs & Squash-Merge)
     └── Subprocess Execution:
          └── [ /usr/local/bin/agy CLI ]  <── Executes in workspace/<project_name>
```

## 5. Technology Stack
- **Backend Language & Runtime**: Python 3.11
- **API Framework**: FastAPI, Uvicorn, Pydantic
- **Core AI Agent Engine**: Google Antigravity CLI flat binary (`agy` v1.3+) pre-installed in `/usr/local/bin/agy`
- **Headless Authentication**: Direct Gemini API connection via `modelProvider: "gemini"` in `~/.gemini/antigravity-cli/settings.json` authenticated with `GEMINI_API_KEY` (with fallback to `AGY_OAUTH_TOKEN` / `~/.gemini/jetski-standalone-oauth-token`)
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
- `core/config.py`: Environment variable loading, GCP project ID (`ai-learning-499409`), Vercel scope settings (`noam-projects2`), `AGY_CLI_PATH` (`/usr/local/bin/agy` or `agy`), and `ensure_agy_settings()` which ensures `settings.json` configures `modelProvider: "gemini"` when `GEMINI_API_KEY` is present. Also provides `ensure_agy_oauth_token()` for optional OAuth token seeding.
- `api/routes.py`: FastAPI routes registering `/api/health`, `/api/projects`, `/api/generate`, `/api/runs/active`, `/api/runs/active/stream`, `/api/runs/cancel`, and file inspection endpoints.
- `services/code_creation.py`: Core CLI execution module.
  - Ensures `settings.json` is configured (`ensure_agy_settings()`) and any credentials are seeded prior to invocation.
  - Spawns the pre-installed `agy` CLI as an asynchronous subprocess with `stdin=asyncio.subprocess.DEVNULL`:
    `agy -p "<prompt>" --dangerously-skip-permissions --print-timeout 600s`
  - When executing within an existing project workspace with previous prompt history or code, passes `--continue` to preserve multi-turn context and conversational memory.
  - Sets the subprocess working directory to the target project workspace (`workspace/<project_name>`).
  - Injects authenticated environment variables (`GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GH_TOKEN`, `PATH`, `HOME`).
  - Asynchronously reads stdout and stderr in real-time non-blocking chunks (`read(4096)`), streaming live output to subscribers, bounded by a 300-second execution timeout.
  - Spawns subprocesses with `start_new_session=True` and prioritizes `proc.wait()`, following with a 2.0s bounded grace period for stream pipe draining so background daemon processes never block execution.
  - Configures git author details (`user.name`, `user.email`, `init.defaultBranch main`) and executes `gh auth setup-git` with `GH_TOKEN` before CLI invocation, giving the CLI full, non-interactive git authentication identical to local Mac execution.
  - Injects `GIT_TERMINAL_PROMPT=0`, `GH_PROMPT_DISABLED=1`, and `GIT_ASKPASS=/bin/echo` into subprocess environments.
  - Intelligently recognizes project names referenced in user prompts across spaces, hyphens, and underscores, auto-routing execution to the target project workspace.
- `services/run_manager.py`: Centralized singleton manager governing code generation background tasks.
  - Decouples task execution from single client connections using `asyncio.create_task`.
  - Retains cumulative session logs across all sequential runs for the active project, prefixing new user commands with clear dividers (`💬 [User] <prompt>`).
  - Tracks the running subprocess handle and PID on `ActiveRun`.
  - Implements `cancel_run(run_id=None)`: terminates child processes (`SIGTERM` followed by `SIGKILL` if ungraceful), cancels the asyncio background task, marks status as `cancelled`, appends a cancellation notice, and broadcasts to subscribers.
  - While `agy` executes, reports `status: "running"`.
  - When `agy` finishes, stores the complete response and sets `status: "completed"`.
  - Enables re-connecting clients (e.g. mobile phone after disconnecting from desktop) to query active run state via `get_active_run()` and receive the cumulative response upon completion.
  - Emits periodic SSE keep-alive heartbeat comments (`: keepalive\n\n`) during execution to prevent intermediate proxies from timing out.
- `services/project_service.py`: Discovers user GitHub repositories via `gh repo list` and REST API as a direct, dynamic reflection of GitHub without inspecting subdirectories. Formats repository catalog records in descending order of `updated_at`. Local workspace directories under `workspace/` serve as the target execution directories for `agy`.
- `services/prompt_service.py`: Maintains append-only sequential user prompt history in `prompt.txt` (`append_numbered_prompt`).
- `services/github_service.py`: Manages git operations and GitHub CLI workflows (cloning, branch creation, PR management, and secret provisioning).
- `services/intent_service.py`: Classifies user prompts (info retrieval, plan confirmation, PR merge) and detects referenced projects using space/hyphen/underscore-normalized fuzzy matching.
- `server.py`: FastAPI application factory with CORS middleware, health routes, and run management endpoints.

## 7. Frontend
The frontend is structured under `frontend/`:
- `src/components/`: Reusable UI modules including `Header`, `Sidebar` (hosting complete project details, stats, deployment links), `FilesDrawer`, `TerminalStream`, `PromptEditor` (clean prompt input with suggestion chips and interactive `⏹️ Stop` cancel action), and modal dialogs.
- `src/services/api.ts`: Typed HTTP client wrapping backend REST endpoints, active run retrieval (`getActiveRun`), cancellation (`cancelActiveRun`), and execution endpoints.
- `src/types/`: Interfaces for projects, generation events, active runs, file trees, and system status.
- `src/App.tsx`: Top-level application state orchestrator:
  - When the user submits a prompt, triggers execution and preserves cumulative session logs in the terminal console, appending a formatted user prompt divider and streaming incoming responses without wiping previous outputs.
  - Renders live line-by-line output as `agy` executes in the background.
  - Provides a one-click `⏹️ Stop` button to cancel stuck or long-running executions, calling `cancelActiveRun()` to immediately terminate the backend process and reset the UI.
  - Handles project creation persistence, active project selection with case-insensitivity, active run auto-detection and re-connection on mount, seamless mobile handover, and mobile view switching (`⚡ Live Console` / `📁 Projects`).
- `src/index.css`: Global styles, dynamic viewport height sizing (`100vh` and `100dvh`), flex-constrained independent scrolling containers, and mobile navigation tab styles.
- `vercel.json`: Routing and static asset caching configuration.


## 8. Data Model
- **Project Structure**:
  ```text
  workspace/
  └── <project-name>/
      ├── prompt.txt         # Numbered prompt log (including plan, confirm, merge)
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
    status: 'idle' | 'running' | 'completed' | 'error' | 'cancelled'
    logs: string
    started_at: number | null
  }
  ```

## 9. API
- `GET /api/health`: Health status endpoint returning status code 200 and system health metadata.
- `GET /api/skills`: Retrieve all dynamically loaded skills mapping skill names to their full markdown contents, remote source repository URL (`skills_source`), and total skill count.
- `GET /api/projects`: List all user GitHub repositories dynamically as a direct reflection of GitHub.
- `GET /api/projects/{project_name}`: Retrieve project details, file list, stats, and README (syncing/cloning from GitHub into `workspace/<project_name>` if needed).
- `GET /api/projects/{name}/files/{file_path}`: Retrieve content and metadata for a specific file in a project.
- `GET /api/runs/active`: Query current active or latest run status, returning `ActiveRunResponse` with accumulated logs.
- `GET /api/runs/active/stream`: Stream ongoing run output (replays buffered history then delivers output once complete) over text/plain or SSE.
- `POST /api/runs/cancel`: Cancel active run immediately, terminating the child process and freeing the server for subsequent prompts.
- `POST /api/runs/{run_id}/cancel`: Cancel a specific run by ID.
- `POST /api/generate`: Initiate execution of the `agy` CLI with the user's prompt on the target project workspace, managing execution via background `RunManager`, and returning the response when the CLI finishes.
- `GET /api/generate`: GET variant of code generation execution endpoint.
- `GET /api/projects/{name}/prompts`: Retrieve history of prompts for the specified project.

## 10. Configuration
The application relies on the following environment variables:
- `GEMINI_API_KEY`: API key for Gemini models and `agy` CLI execution. When present, the system auto-configures `~/.gemini/antigravity-cli/settings.json` with `"modelProvider": "gemini"` to enable direct API execution without OAuth prompts.
- `AGY_OAUTH_TOKEN`: Optional JSON content of `jetski-standalone-oauth-token` injected into the container/server. When present, the backend auto-populates `~/.gemini/jetski-standalone-oauth-token`.
- `GH_TOKEN` / `GITHUB_TOKEN`: GitHub personal access token or OAuth token with `repo` and `workflow` scopes for repository and workflow management.
- `AGY_CLI_PATH`: Path to the pre-installed Antigravity CLI executable (default: `/usr/local/bin/agy` or `agy`).
- `AGENT_WORKSPACE`: Relative or absolute path to the local project workspace (default: `workspace`).
- `AGENT_DOCS_DIR`: Optional custom path to the documentation folder containing `prompt.md` (default: auto-detected `backend/src/remote_code_agent/services/docs/`).
- `SKILLS_REPO_URL`: URL to the remote GitHub repository skills directory (default: `https://github.com/noam2030/build-with-agent/tree/main/.agents/skills`).
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
  - `test_code_creation.py`: Pre-installed `agy` CLI subprocess execution, argument construction (`-p <prompt> --dangerously-skip-permissions`), multi-turn session continuation flag (`--continue`), workspace directory handling (`cwd`), environment variable propagation (`GEMINI_API_KEY`, `GH_TOKEN`), automatic `settings.json` configuration (`modelProvider: "gemini"`), token seeding, quota/error capture, live chunk streaming (`read(4096)`), safe pipe draining, timeout handling, and response delivery.
  - `test_api_routes.py`: REST endpoint verification (including `/api/runs/active`, `/api/runs/active/stream`, and `/api/runs/cancel`).
  - `test_run_manager.py`: Background task orchestration, cumulative session log retention, run cancellation, subprocess termination, multi-subscriber queues, buffered log replaying, and state retention.
  - `test_github_service.py`: Git operations, branch creation, feature branch push, PR creation, squash-merging, and secret synchronization.
  - `test_intent_service.py`: Classification of user prompts (info retrieval, confirmation requests, merge requests, code mutation requests, and space/hyphen normalized project detection).
  - `test_project_service.py`: GitHub repository catalog discovery, most-recently-updated ordering matching GitHub, workspace scanning, dedicated repo sync, and cleanup.
  - `test_prompt_service.py`: `prompt.txt` manipulation.
  - `test_server.py`: FastAPI application startup, CORS verification, root metadata, and health endpoint verification.
  - `test_ci_workflows.py`: Verification of CI/CD workflow definitions, trigger configurations, and security secret requirements.

## 12. Deployment
- **Target Backend Platform**: Google Cloud Run (Fully managed serverless).
- **Target Project**: `ai-learning-499409`.
- **Region**: `us-central1`.
- **Production Backend Service Name**: `remote-code-agent`.
- **Production Backend URL**: `https://remote-code-agent-289332143182.us-central1.run.app`.
- **Staging Backend Service Name**: `remote-code-agent-staging`.
- **Frontend Target Platform**: Vercel (`https://remote-code-agent-ui.vercel.app`), configured with `VITE_API_URL=https://remote-code-agent-289332143182.us-central1.run.app`.
- **Container Build**: Docker build strictly from single root `Dockerfile` using Python 3.11-slim. It installs Git, curl, ca-certificates, GitHub CLI (`gh`), and pre-installs the official flat `agy` CLI binary directly into `/usr/local/bin/agy` via `curl -fsSL https://antigravity.google/cli/install.sh | bash -s -- -d /usr/local/bin`.
- **Port**: Container listens on port `8080`.
- **Request Timeout**: Configured with `--timeout=3600` (up to 60 minutes) to support multi-step agent code generation and build processes without premature HTTP connection drops.
- **Access**: Unauthenticated invocations enabled (`--allow-unauthenticated`).
- **CI/CD Architecture**:
  - **Pull Request Verification (`.github/workflows/pr-verify.yml`)**: Runs backend tests and frontend build on PRs targeting `main`.
  - **Optional Staging Deployment (`.github/workflows/deploy-staging.yml`)**: On-demand dispatch.
  - **Production Deployment (`.github/workflows/deploy-prod.yml`)**:
    - Triggered automatically on push / merge to `main`.
    - Runs backend automated tests and frontend build validation.
    - Deploys backend API to Google Cloud Run production (`remote-code-agent`), forwarding `GEMINI_API_KEY` and `AGY_OAUTH_TOKEN` secrets to provide headless `agy` CLI execution.
    - Deploys frontend UI to Vercel production (`--prod`) targeting the project scope and setting `VITE_API_URL` to the production backend URL.


