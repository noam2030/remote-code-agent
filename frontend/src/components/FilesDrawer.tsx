import React from 'react'
import type { Project, ProjectFileDetail } from '../types'

interface FilesDrawerProps {
  project: Project | null
  isOpen: boolean
  onOpenFile: (filePath: string) => void
}

export const FilesDrawer: React.FC<FilesDrawerProps> = ({
  project,
  isOpen,
  onOpenFile,
}) => {
  if (!isOpen || !project) return null

  const files: ProjectFileDetail[] =
    project.files_detail && project.files_detail.length > 0
      ? project.files_detail
      : (project.files || []).map((p) => ({
          path: p,
          lines: 0,
          size_bytes: 0,
          is_binary: false,
        }))

  return (
    <div className="files-panel">
      <div className="files-header">
        <span>
          Files in this project{' '}
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 'normal', marginLeft: '0.4rem' }}>
            (Click to view content)
          </span>
        </span>
        <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Synced with workspace</span>
      </div>
      <div className="files-list">
        {files.length === 0 ? (
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>No files generated yet.</span>
        ) : (
          files.map((file) => (
            <div
              key={file.path}
              className="file-item-card"
              onClick={() => onOpenFile(file.path)}
            >
              <div className="file-item-main">
                <span>📄</span>
                <span className="file-item-path">{file.path}</span>
              </div>
              <div className="file-item-meta">
                {file.lines > 0 && (
                  <span className="file-pill file-pill-loc">{file.lines} LOC</span>
                )}
                {file.size_bytes > 0 && (
                  <span className="file-pill">{(file.size_bytes / 1024).toFixed(1)} KB</span>
                )}
                <span className="file-item-btn">View →</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
