import type {
  ActiveRunResponse,
  FileContentResponse,
  LoadedSkillsResponse,
  Project,
  ProjectDetail,
} from '../types'


const STORAGE_KEY_BACKEND = 'rca_backend_url'
export const DEFAULT_PRODUCTION_BACKEND_URL =
  'https://remote-code-agent-289332143182.us-central1.run.app'

export function getBackendUrl(): string {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem(STORAGE_KEY_BACKEND)
    if (custom && custom.trim()) {
      // Discard deprecated/stale backend URL if stored in browser localStorage
      if (custom.includes('702552270447')) {
        localStorage.removeItem(STORAGE_KEY_BACKEND)
      } else {
        return custom.trim().replace(/\/+$/, '')
      }
    }
  }
  const envUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
  if (envUrl) {
    return envUrl
  }

  // When hosted remotely (e.g. on Vercel) without env var, default to the production backend
  if (
    typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1'
  ) {
    return DEFAULT_PRODUCTION_BACKEND_URL
  }

  return ''
}

export function setBackendUrl(url: string): void {
  if (typeof window !== 'undefined') {
    if (url && url.trim()) {
      localStorage.setItem(STORAGE_KEY_BACKEND, url.trim().replace(/\/+$/, ''))
    } else {
      localStorage.removeItem(STORAGE_KEY_BACKEND)
    }
  }
}

function resolveUrl(path: string): string {
  const base = getBackendUrl()
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return base ? `${base}${cleanPath}` : cleanPath
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(resolveUrl('/api/projects'))
  if (!res.ok) {
    throw new Error(`Failed to list projects: HTTP ${res.status}`)
  }
  return res.json()
}

export async function getProject(name: string): Promise<ProjectDetail> {
  const res = await fetch(resolveUrl(`/api/projects/${encodeURIComponent(name)}`))
  if (!res.ok) {
    throw new Error(`Failed to fetch project '${name}': HTTP ${res.status}`)
  }
  return res.json()
}

export async function getFileContent(
  project: string,
  filePath: string
): Promise<FileContentResponse> {
  const res = await fetch(
    resolveUrl(`/api/projects/${encodeURIComponent(project)}/files/${encodeURI(filePath)}`)
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to read file '${filePath}': HTTP ${res.status}`)
  }
  return res.json()
}


function filterStreamChunk(raw: string): string {
  if (!raw) return ''
  // If the chunk consists entirely of SSE comment lines (e.g. : keepalive\n\n or : connected\n\n), discard it
  const lines = raw.split('\n')
  const nonCommentLines = lines.filter((line) => {
    const trimmed = line.trim()
    return trimmed.length > 0 && !trimmed.startsWith(':')
  })
  if (nonCommentLines.length === 0) return ''
  return lines.filter((line) => !line.trimStart().startsWith(':')).join('\n')
}

export async function generateCodeStream(
  prompt: string,
  projectName: string | undefined,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal,
  offset?: number
): Promise<void> {
  const query = new URLSearchParams()
  query.set('prompt', prompt)
  if (projectName) {
    query.set('project_name', projectName)
  }
  if (offset !== undefined && offset > 0) {
    query.set('offset', offset.toString())
  }
  const url = resolveUrl(`/api/generate?${query.toString()}`)

  const response = await fetch(url, {
    signal,
    headers: {
      Accept: 'text/plain; charset=utf-8',
    },
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => '')
    throw new Error(errText || `Code generation failed: HTTP ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('ReadableStream not supported by browser environment.')
  }

  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    const filtered = filterStreamChunk(chunk)
    if (filtered) {
      onChunk(filtered)
    }
  }
}

export async function getActiveRun(): Promise<ActiveRunResponse> {
  const res = await fetch(resolveUrl('/api/runs/active'))
  if (!res.ok) {
    throw new Error(`Failed to fetch active run: HTTP ${res.status}`)
  }
  return res.json()
}

export async function streamActiveRun(
  offset: number = 0,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const url = resolveUrl(`/api/runs/active/stream?offset=${encodeURIComponent(offset)}`)
  const response = await fetch(url, {
    signal,
    headers: {
      Accept: 'text/plain; charset=utf-8',
    },
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => '')
    throw new Error(errText || `Failed to stream active run: HTTP ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('ReadableStream not supported by browser environment.')
  }

  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    const filtered = filterStreamChunk(chunk)
    if (filtered) {
      onChunk(filtered)
    }
  }
}

export async function getLoadedSkills(): Promise<LoadedSkillsResponse> {
  const res = await fetch(resolveUrl('/api/skills'))
  if (!res.ok) {
    throw new Error(`Failed to fetch loaded skills: HTTP ${res.status}`)
  }
  return res.json()
}

export async function cancelActiveRun(runId?: string): Promise<ActiveRunResponse> {
  const url = resolveUrl(runId ? `/api/runs/${encodeURIComponent(runId)}/cancel` : '/api/runs/cancel')
  const res = await fetch(url, {
    method: 'POST',
  })
  if (!res.ok) {
    const errText = await res.text().catch(() => '')
    throw new Error(errText || `Failed to cancel run: HTTP ${res.status}`)
  }
  return res.json()
}


