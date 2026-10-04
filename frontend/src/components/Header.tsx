import React from 'react'
import type { Project } from '../types'

interface HeaderProps {
  project: Project | null
  onToggleFiles: () => void
  onOpenMasterPrompt: () => void
  onOpenDelete: () => void
  onOpenSettings: () => void
  filesOpen: boolean
}

export const Header: React.FC<HeaderProps> = ({
  project,
  onToggleFiles,
  onOpenMasterPrompt,
  onOpenDelete,
  onOpenSettings,
  filesOpen,
}) => {
  const hasPromptTxt =
    project &&
    ((project.files && project.files.includes('prompt.txt')) ||
      (project.files_detail && project.files_detail.some((f) => f.path === 'prompt.txt')))

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="logo-badge">
          <span className="logo-icon">🚀</span>
          <div>
            <h1 className="logo-text">Remote Code Agent</h1>
            <span className="version-tag">TypeScript &bull; Cloud Run &bull; Vercel</span>
          </div>
        </div>
      </div>

      <div className="header-center">
        {project ? (
          <div className="active-project-bar">
            <span className="project-badge">Project: {project.name}</span>
            <span className="stat-pill">{project.lines_of_code.toLocaleString()} LOC</span>
            <span className="stat-pill">{project.tokens_spent.toLocaleString()} Tokens</span>
            {project.cloud_run_url && (
              <a
                href={project.cloud_run_url}
                target="_blank"
                rel="noreferrer"
                className="stat-pill live-pill"
              >
                🌐 Live App
              </a>
            )}
          </div>
        ) : (
          <span className="no-project-selected">Select or create a project to start coding</span>
        )}
      </div>

      <div className="header-right">
        {project && (
          <>
            <a
              href={project.github_url}
              target="_blank"
              rel="noreferrer"
              className="btn-action"
              title="View on GitHub"
            >
              🐙 GitHub
            </a>
            {hasPromptTxt && (
              <button
                className="btn-action"
                onClick={onOpenMasterPrompt}
                title="View consolidated prompt.txt specification"
              >
                📋 Master Prompt
              </button>
            )}
            <button
              className={`btn-action ${filesOpen ? 'btn-active' : ''}`}
              onClick={onToggleFiles}
              title="Toggle Project Files Drawer"
            >
              📂 Files ({project.files_count || (project.files_detail ? project.files_detail.length : 0)})
            </button>
            <button
              className="btn-action btn-danger-action"
              onClick={onOpenDelete}
              title="Delete Project"
            >
              🗑️ Delete
            </button>
          </>
        )}
        <button className="btn-icon" onClick={onOpenSettings} title="Settings">
          ⚙️
        </button>
      </div>
    </header>
  )
}
