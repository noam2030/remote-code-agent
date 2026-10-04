import React, { useState } from 'react'
import type { Project } from '../types'

interface SidebarProps {
  projects: Project[]
  selectedProject: Project | null
  loading: boolean
  onSelectProject: (project: Project | null) => void
  onRefresh: () => void
  onDeleteProject?: (project: Project) => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  projects,
  selectedProject,
  loading,
  onSelectProject,
  onRefresh,
  onDeleteProject,
}) => {
  const [search, setSearch] = useState('')
  const [showNewBox, setShowNewBox] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')

  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return
    const name = newProjectName.trim()
    setNewProjectName('')
    setShowNewBox(false)
    // Select placeholder project for creation
    onSelectProject({
      name,
      cloud_run_url: null,
      github_url: `https://github.com/noam2030/remote-code-agent-output/tree/main/${name}`,
      has_remote: false,
      is_local: false,
      files: [],
      files_detail: [],
      lines_of_code: 0,
      tokens_spent: 0,
      files_count: 0,
      stats: {},
    })
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">
          <span>📁 Projects</span>
          <span className="count-badge">{projects.length}</span>
        </div>
        <div className="sidebar-actions">
          <button
            className="icon-btn"
            onClick={onRefresh}
            disabled={loading}
            title="Refresh project list"
          >
            🔄
          </button>
          <button
            className="icon-btn"
            onClick={() => setShowNewBox((prev) => !prev)}
            title="Create new project"
          >
            + New
          </button>
        </div>
      </div>

      {showNewBox && (
        <form className="create-project-box" onSubmit={handleCreateSubmit}>
          <div className="create-input-group">
            <input
              type="text"
              className="create-input"
              placeholder="project-name (e.g. todo-app)"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              autoFocus
            />
            <button type="submit" className="btn-create">
              Create
            </button>
          </div>
        </form>
      )}

      <div className="search-box">
        <input
          type="text"
          className="search-input"
          placeholder="🔍 Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="project-list">
        {loading && projects.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            Loading projects...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            {search ? 'No projects match search.' : 'No projects found.'}
          </div>
        ) : (
          filtered.map((proj) => {
            const isActive = selectedProject?.name === proj.name
            const fileCount = proj.files_count || (proj.files_detail ? proj.files_detail.length : 0)

            return (
              <div
                key={proj.name}
                className={`project-card ${isActive ? 'active' : ''}`}
                onClick={() => onSelectProject(proj)}
              >
                <div className="project-card-header">
                  <div className="project-card-title">
                    <span>📁</span>
                    <span>{proj.name}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {isActive && <span className="active-tag">ACTIVE</span>}
                    {onDeleteProject && (
                      <button
                        className="btn-card-delete"
                        title="Delete project"
                        onClick={(e) => {
                          e.stopPropagation()
                          onDeleteProject(proj)
                        }}
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </div>

                <div className="project-links">
                  {proj.cloud_run_url && (
                    <a
                      href={proj.cloud_run_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="project-tag tag-live"
                      onClick={(e) => e.stopPropagation()}
                    >
                      🚀 Live App
                    </a>
                  )}
                  <a
                    href={proj.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="project-tag tag-github"
                    onClick={(e) => e.stopPropagation()}
                  >
                    🐙 GitHub
                  </a>
                  <span className="project-tag tag-files">📄 {fileCount} files</span>
                  <span className="project-tag tag-loc">
                    📝 {proj.lines_of_code.toLocaleString()} LOC
                  </span>
                  <span className="project-tag tag-tokens">
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
