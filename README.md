# Remote Code Agent - Monorepo

Autonomous AI code generation platform built with the [Google Antigravity SDK](https://github.com/google/antigravity), featuring a modern TypeScript frontend optimized for [Vercel](https://vercel.com) and a FastAPI backend deployed on Google Cloud Run.

## Architecture & Structure

```text
remote-code-agent/
├── frontend/               # Modern TypeScript React application (Vercel)
│   ├── src/
│   │   ├── components/     # UI components (Header, Sidebar, Terminal, Modals)
│   │   ├── services/       # API client & SSE stream reader
│   │   ├── types/          # TypeScript interfaces
│   │   ├── App.tsx         # Main dashboard orchestrator
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── vercel.json         # Vercel deployment configuration
│   └── README.md
│
├── backend/                # Standard Python FastAPI backend (Cloud Run)
│   ├── src/
│   │   └── remote_code_agent/
│   │       ├── api/        # REST routes & endpoints (/api/projects, /api/health)
│   │       ├── core/       # Configuration & environment variables
│   │       ├── services/   # Business logic (code generation, github, prompt)
│   │       ├── main.py     # Entrypoint
│   │       └── server.py   # FastAPI app with CORS middleware
│   ├── tests/              # Comprehensive automated unit & integration test suite
│   ├── Dockerfile          # Cloud Run container definition
│   ├── pyproject.toml      # Backend package definition
│   ├── requirements.txt
│   └── README.md
│
├── .github/workflows/      # Automated CI/CD pipelines
│   ├── deploy-prod.yml     # Automated production deployment to Google Cloud Run
│   └── pr-staging.yml      # PR verification & staging deployment
│
├── Dockerfile              # Root container builder forwarding to backend
├── requirements.txt        # Root requirements forwarding to backend
└── README.md
```

## Quick Start

### 1. Backend (FastAPI & Antigravity SDK)

```bash
cd backend
pip install -r requirements.txt
uv run python -m remote_code_agent.main
```
The backend API runs on `http://localhost:8080`.

### 2. Frontend (TypeScript & Vite)

```bash
cd frontend
npm install
npm run dev
```
The frontend application runs on `http://localhost:3000` and proxies API requests to `http://localhost:8080`.

## Deployment

### Backend: Google Cloud Run
Deployment is fully automated through GitHub Actions upon merging to `main`:
- **Production Service**: `remote-code-agent`
- **Region**: `us-central1`
- **URL**: `https://remote-code-agent-702552270447.us-central1.run.app`

### Frontend: Vercel
The frontend is pre-configured for instant zero-configuration deployment to Vercel:
1. Import this repository in the [Vercel Dashboard](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set **Framework Preset** to `Vite`.
4. Configure environment variable `VITE_API_URL` pointing to your Cloud Run service URL.
5. Deploy!
