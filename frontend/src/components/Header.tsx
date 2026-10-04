import React from 'react'

export const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-logo">⚡</div>
        <div className="brand-text">
          <h1>Remote Code Agent</h1>
          <p>Google Antigravity Agent Service • Cloud Run &amp; GitHub Continuous Deployment</p>
        </div>
      </div>
      <div className="header-actions">
        <div className="status-pill">
          <span className="status-dot"></span>
          <span>Connected to Agent</span>
        </div>
        <a
          href="https://github.com/noam2030/remote-code-agent-output"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-btn"
        >
          🐙 GitHub Central Repo
        </a>
        <a
          href="https://remote-code-agent-702552270447.us-central1.run.app/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-btn"
        >
          📖 API Docs
        </a>
      </div>
    </header>
  )
}
