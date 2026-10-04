import React from 'react'
import type { Project } from '../types'

interface TargetProjectBannerProps {
  project: Project | null
  filesCount: number
  filesOpen: boolean
  onToggleFiles: () => void
  onOpenMasterPrompt: () => void
  onOpenDelete: () => void
}

export const TargetProjectBanner: React.FC<TargetProjectBannerProps> = ({
  project,
  filesCount,
  filesOpen,
  onToggleFiles,
  onOpenMasterPrompt,
  onOpenDelete,
}) => {
  if (!project) {
    return (
      <div className="active-project-banner">
        <div className="banner-title">
          <span className="banner-sub">Target Project</span>
          <h2 className="banner-name">Select a project</h2>
          <div className="banner-stats-row">
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Choose a project from the left sidebar or create a new one to begin.
            </span>
          </div>
        </div>
      </div>
    )
  }

  const hasPromptTxt =
    Boolean(project.files && project.files.includes('prompt.txt')) ||
    Boolean(project.files_detail && project.files_detail.some((f) => f.path === 'prompt.txt'))

  return (
    <div className="active-project-banner">
      <div className="banner-title">
        <span className="banner-sub">TARGET PROJECT</span>
        <h2 className="banner-name">{project.name}</h2>
        <div className="banner-stats-row">
          <div className="banner-stat-pill" title="Total Lines of Code">
            <span className="stat-icon">📝</span>
            <span className="stat-label">Code:</span>
            <strong className="stat-val">{project.lines_of_code.toLocaleString()} LOC</strong>
          </div>
          <div className="banner-stat-pill" title="Tokens Spent Building Project">
            <span className="stat-icon">🪙</span>
            <span className="stat-label">Tokens Spent:</span>
            <strong className="stat-val">{project.tokens_spent.toLocaleString()}</strong>
          </div>
          <div className="banner-stat-pill" title="Total Project Files">
            <span className="stat-icon">📁</span>
            <span className="stat-label">Files:</span>
            <strong className="stat-val">{filesCount}</strong>
          </div>
          <div
            className="banner-stat-pill"
            title="Persistent Data Stored in Google Cloud Firestore"
            style={{
              borderColor: 'rgba(245, 158, 11, 0.4)',
              background: 'rgba(245, 158, 11, 0.1)',
            }}
          >
            <span className="stat-icon">🔥</span>
            <span className="stat-label">Firestore:</span>
            <strong className="stat-val" style={{ color: '#fbbf24' }}>
              {project.name}
            </strong>
          </div>
        </div>
      </div>

      <div className="banner-actions">
        {project.cloud_run_url && (
          <a
            href={project.cloud_run_url}
            target="_blank"
            rel="noopener noreferrer"
            className="action-btn action-btn-primary"
          >
            🚀 Open Live Cloud Run App
          </a>
        )}
        <a
          href={project.github_url}
          target="_blank"
          rel="noopener noreferrer"
          className="action-btn action-btn-secondary"
        >
          🐙 View on GitHub
        </a>
        {hasPromptTxt && (
          <button
            className="action-btn action-btn-secondary"
            onClick={onOpenMasterPrompt}
            title="View prompt.txt master specification"
          >
            📋 Master Prompt
          </button>
        )}
        <button
          className={`action-btn action-btn-secondary ${filesOpen ? 'active' : ''}`}
          onClick={onToggleFiles}
        >
          📁 Project Files ( {filesCount} )
        </button>
        <button className="action-btn action-btn-danger" onClick={onOpenDelete}>
          🗑️ Delete Project
        </button>
      </div>
    </div>
  )
}
