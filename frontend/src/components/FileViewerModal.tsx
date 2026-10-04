import React, { useState } from 'react'
import type { FileContentResponse } from '../types'

interface FileViewerModalProps {
  file: FileContentResponse | null
  loading: boolean
  onClose: () => void
}

export const FileViewerModal: React.FC<FileViewerModalProps> = ({ file, loading, onClose }) => {
  const [copied, setCopied] = useState(false)

  if (!file && !loading) return null

  const handleCopy = () => {
    if (file?.content) {
      navigator.clipboard.writeText(file.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const lines = file?.content ? file.content.split('\n') : []

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="file-icon">📄</span>
            <div>
              <h3 className="modal-title">{file?.path || 'Loading file...'}</h3>
              <p className="modal-subtitle">
                Project: <strong>{file?.project}</strong> &bull; {file?.lines.toLocaleString()} lines &bull;{' '}
                {file ? (file.size_bytes / 1024).toFixed(1) : 0} KB
              </p>
            </div>
          </div>
          <div className="modal-actions">
            {file && !file.is_binary && file.content && (
              <button className="btn-secondary btn-sm" onClick={handleCopy}>
                {copied ? '✅ Copied' : '📋 Copy Content'}
              </button>
            )}
            <button className="btn-close" onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="loading-spinner">Loading file content...</div>
          ) : file?.is_binary ? (
            <div className="binary-notice">
              <span className="binary-icon">📦</span>
              <p>Binary file cannot be displayed in text viewer.</p>
            </div>
          ) : (
            <div className="code-viewer">
              <div className="line-numbers">
                {lines.map((_, i) => (
                  <span key={i}>{i + 1}</span>
                ))}
              </div>
              <pre className="code-content">
                <code>{file?.content}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
