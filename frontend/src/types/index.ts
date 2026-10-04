export interface ProjectFileDetail {
  path: string
  lines: number
  size_bytes: number
  is_binary: boolean
}

export interface ProjectStats {
  total_tokens?: number
  prompt_tokens?: number
  completion_tokens?: number
  build_runs?: number
  last_updated?: string
}

export interface Project {
  name: string
  github_url: string
  cloud_run_url: string | null
  has_remote: boolean
  is_local: boolean
  files: string[]
  files_count: number
  files_detail: ProjectFileDetail[]
  lines_of_code: number
  tokens_spent: number
  stats: ProjectStats
}

export interface ProjectDetail extends Project {
  readme_content?: string
}

export interface FileContentResponse {
  project: string
  path: string
  lines: number
  size_bytes: number
  is_binary: boolean
  content: string | null
}
