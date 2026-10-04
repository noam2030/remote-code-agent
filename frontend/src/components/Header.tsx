import React from 'react'

export const Header: React.FC = () => {
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
        <a
          href="https://github.com/noam2030/remote-code-agent-output"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-btn"
        >
          🐙 <span className="nav-btn-text-full">GitHub Central Repo</span>
          <span className="nav-btn-text-short">GitHub</span>
        </a>
        <a
          href="https://remote-code-agent-702552270447.us-central1.run.app/docs"
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
