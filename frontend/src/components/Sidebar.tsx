import React, { useState } from 'react'
import type { Project } from '../types'

interface SidebarProps {
  projects: Project[]
  selectedProject: Project | null
  loading: boolean
  onSelectProject: (project: Project | null) => void
  onRefresh: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  projects,
  selectedProject,
  loading,
  onSelectProject,
  onRefresh,
}) => {
  const [search, setSearch] = useState('')

  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title-row">
          <h2 className="sidebar-title">📁 Projects ({projects.length})</h2>
          <button className="btn-icon-sm" onClick={onRefresh} disabled={loading} title="Refresh">
            🔄
          </button>
        </div>
        <button
          className={`btn-new-project ${!selectedProject ? 'btn-active-new' : ''}`}
          onClick={() => onSelectProject(null)}
        >
          ✨ + New Project
        </button>
        <input
          type="text"
          className="search-input"
          placeholder="Filter projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="sidebar-list">
        {loading && projects.length === 0 ? (
          <div className="sidebar-loading">Loading projects...</div>
        ) : filtered.length === 0 ? (
          <div className="sidebar-empty">
            {search ? 'No projects match filter' : 'No projects found'}
          </div>
        ) : (
          filtered.map((proj) => {
            const isSelected = selectedProject?.name === proj.name
            const fileCount = proj.files_count || (proj.files_detail ? proj.files_detail.length : 0)

            return (
              <div
                key={proj.name}
                className={`project-card ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectProject(proj)}
              >
                <div className="card-top">
                  <span className="project-name">{proj.name}</span>
                  {proj.cloud_run_url && (
                    <span className="live-dot" title="Live on Google Cloud Run">
                      ● live
                    </span>
                  )}
                </div>

                <div className="card-badges">
                  <span className="card-badge" title="Files count">
                    📄 {fileCount}
                  </span>
                  <span className="card-badge" title="Lines of Code">
                    📝 {proj.lines_of_code.toLocaleString()} LOC
                  </span>
                  <span className="card-badge" title="Tokens spent">
                    🪙 {proj.tokens_spent.toLocaleString()}
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </aside>
  )
}
