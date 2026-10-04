import type { FileContentResponse, Project, ProjectDetail } from '../types'

const STORAGE_KEY_BACKEND = 'rca_backend_url'

export function getBackendUrl(): string {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem(STORAGE_KEY_BACKEND)
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/+$/, '')
    }
  }
  const envUrl = import.meta.env.VITE_API_URL || ''
  return envUrl.replace(/\/+$/, '')
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

export async function deleteProject(
  name: string,
  deleteRemote = true
): Promise<{ status: string; message: string; project: string }> {
  const res = await fetch(
    resolveUrl(
      `/api/projects/${encodeURIComponent(name)}?delete_remote=${deleteRemote ? 'true' : 'false'}`
    ),
    { method: 'DELETE' }
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to delete project '${name}': HTTP ${res.status}`)
  }
  return res.json()
}

export async function generateCodeStream(
  prompt: string,
  projectName: string | undefined,
  onChunk: (chunk: string) => void
): Promise<void> {
  const url = resolveUrl(
    `/api/generate?prompt=${encodeURIComponent(prompt)}${
      projectName ? `&project_name=${encodeURIComponent(projectName)}` : ''
    }`
  )

  const response = await fetch(url, {
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
    if (chunk) {
      onChunk(chunk)
    }
  }
}
