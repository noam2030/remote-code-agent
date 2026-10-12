import React from 'react'
import { getBackendUrl } from '../services/api'

interface HeaderProps {
  onOpenSkills?: () => void
  skillsCount?: number
}

export const Header: React.FC<HeaderProps> = ({ onOpenSkills, skillsCount }) => {
  const backendBase = getBackendUrl() || 'https://remote-code-agent-289332143182.us-central1.run.app'
  const docsUrl = `${backendBase}/docs`

  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-logo">⚡</div>
        <div className="brand-text">
          <h1>Remote Code Agent</h1>
          <p className="brand-subtitle">
            Google Antigravity Agent Service • Cloud Run &amp; GitHub Continuous Deployment
          </p>
        </div>
      </div>
      <div className="header-actions">
        <div className="status-pill">
          <span className="status-dot"></span>
          <span className="status-text-full">Connected to Agent</span>
          <span className="status-text-short">Connected</span>
        </div>
        <button
          type="button"
          onClick={onOpenSkills}
          className="nav-btn"
          title="View dynamically loaded agent skills"
        >
          🧠 <span className="nav-btn-text-full">Skills{skillsCount !== undefined && skillsCount > 0 ? ` (${skillsCount})` : ''}</span>
          <span className="nav-btn-text-short">Skills</span>
        </button>
        <a
          href="https://github.com/noam2030"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-btn"
        >
          🐙 <span className="nav-btn-text-full">GitHub Profile</span>
          <span className="nav-btn-text-short">GitHub</span>
        </a>
        <a
          href={docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="nav-btn"
        >
          📖 <span className="nav-btn-text-full">API Docs</span>
          <span className="nav-btn-text-short">Docs</span>
        </a>
      </div>
    </header>
  )
}
