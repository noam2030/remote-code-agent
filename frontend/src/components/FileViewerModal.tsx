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
  const fileName = file?.path ? file.path.split('/').pop() : 'Loading...'

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="file-modal-header">
          <div className="file-modal-title">
            <span style={{ fontSize: '1.1rem' }}>📄</span>
            <div style={{ overflow: 'hidden' }}>
              <h3>{fileName}</h3>
              <div className="file-modal-path">{file?.path}</div>
            </div>
          </div>
          <div className="file-modal-meta">
            {file && (
              <>
                <span className="meta-pill">{file.lines} lines</span>
                <span className="meta-pill">{(file.size_bytes / 1024).toFixed(1)} KB</span>
                {!file.is_binary && (
                  <button
                    className="action-btn action-btn-secondary"
                    onClick={handleCopy}
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                  >
                    {copied ? '✅ Copied' : '📋 Copy'}
                  </button>
                )}
              </>
            )}
            <button className="modal-close-btn" onClick={onClose} title="Close">
              ✕
            </button>
          </div>
        </div>

        <div className="file-modal-body">
          {loading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-dim)', width: '100%' }}>
              ⏳ Loading file content...
            </div>
          ) : file?.is_binary ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', width: '100%' }}>
              📦 This is a binary file and cannot be previewed directly as text.
            </div>
          ) : (
            <div className="code-container">
              <div className="line-numbers">
                {lines.map((_, i) => (
                  <div key={i}>{i + 1}</div>
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
