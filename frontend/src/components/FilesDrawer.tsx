import React from 'react'
import type { Project, ProjectFileDetail } from '../types'

interface FilesDrawerProps {
  project: Project | null
  isOpen: boolean
  onClose: () => void
  onOpenFile: (filePath: string) => void
}

export const FilesDrawer: React.FC<FilesDrawerProps> = ({
  project,
  isOpen,
  onClose,
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
    <div className="files-drawer">
      <div className="drawer-header">
        <h3 className="drawer-title">
          📂 Files in {project.name} ({files.length})
        </h3>
        <button className="btn-close" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="drawer-list">
        {files.length === 0 ? (
          <div className="drawer-empty">No files generated yet.</div>
        ) : (
          files.map((file) => (
            <div
              key={file.path}
              className="drawer-file-item"
              onClick={() => onOpenFile(file.path)}
            >
              <div className="file-info">
                <span className="file-icon">📄</span>
                <span className="file-path">{file.path}</span>
              </div>
              <div className="file-meta">
                {file.lines > 0 && <span className="meta-pill">{file.lines} L</span>}
                {file.size_bytes > 0 && (
                  <span className="meta-pill">{(file.size_bytes / 1024).toFixed(1)} KB</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
