# Remote Code Agent - TypeScript Frontend

A modern, responsive TypeScript single-page application built with React, Vite, and modern web standards, designed for deployment on [Vercel](https://vercel.com).

## Features

- **Project Explorer & Metrics**: Live directory tree with Lines of Code (LOC) calculation, cumulative token spend tracking, and Cloud Run live app links.
- **Canonical Master Specification Viewer**: Inspect and copy `prompt.txt` directly from the dashboard.
- **Interactive Code Viewer**: In-browser inspection of any project file with line numbering and copy functionality.
- **Real-Time Streaming Terminal**: Live agent thought tracking, tool invocation cards, and generation log streaming with auto-scroll.
- **Vercel-Optimized**: Pre-configured `vercel.json` with SPA routing and security headers.
- **Dynamic Backend Targeting**: Seamlessly switches between local development proxy and production Cloud Run backend.

## Local Development

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:3000` and automatically proxy `/api` and `/generate` to the local backend on `http://localhost:8080`.

## Production Build

```bash
npm run build
```

Build outputs are generated in the `dist/` directory.

## Deploying to Vercel

### Option 1: Vercel GitHub Integration (Recommended)

1. In your [Vercel Dashboard](https://vercel.com/dashboard), click **Add New Project**.
2. Import the `remote-code-agent` GitHub repository.
3. Configure **Root Directory**: `frontend`.
4. Framework Preset: **Vite**.
5. Add Environment Variable:
   - `VITE_API_URL`: `https://remote-code-agent-289332143182.us-central1.run.app` (or your Google Cloud Run backend URL).
6. Click **Deploy**.

### Option 2: Vercel CLI

```bash
npm install -g vercel
cd frontend
vercel
```

Follow the prompts:
- Link to existing project: No
- What's the project name: `remote-code-agent-ui`
- In which directory is your code located: `./`
- Want to modify these settings: No

Then deploy to production:
```bash
vercel --prod --build-env VITE_API_URL="https://remote-code-agent-289332143182.us-central1.run.app"
```
