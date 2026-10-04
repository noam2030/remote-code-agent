import React, { useState } from 'react'
import type { FileContentResponse } from '../types'

interface MasterPromptModalProps {
  promptFile: FileContentResponse | null
  loading: boolean
  onClose: () => void
}

export const MasterPromptModal: React.FC<MasterPromptModalProps> = ({ promptFile, loading, onClose }) => {
  const [copied, setCopied] = useState(false)

  if (!promptFile && !loading) return null

  const handleCopy = () => {
    if (promptFile?.content) {
      navigator.clipboard.writeText(promptFile.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const lines = promptFile?.content ? promptFile.content.split('\n') : []

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="file-modal-header">
          <div className="file-modal-title">
            <span style={{ fontSize: '1.1rem' }}>📋</span>
            <div style={{ overflow: 'hidden' }}>
              <h3>Master Prompt (prompt.txt)</h3>
              <div className="file-modal-path">
                {promptFile?.project ? `${promptFile.project}/prompt.txt` : 'prompt.txt'}
              </div>
            </div>
          </div>
          <div className="file-modal-meta">
            <span className="meta-pill">{lines.length} lines</span>
            {promptFile?.content && (
              <button
                className="action-btn action-btn-secondary"
                onClick={handleCopy}
                style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
              >
                {copied ? '✅ Copied' : '📋 Copy Prompt'}
              </button>
            )}
            <button className="modal-close-btn" onClick={onClose} title="Close">
              ✕
            </button>
          </div>
        </div>

        <div className="file-modal-body">
          {loading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-dim)', width: '100%' }}>
              ⏳ Loading prompt.txt...
            </div>
          ) : (
            <div className="code-container">
              <div className="line-numbers">
                {lines.map((_, i) => (
                  <div key={i}>{i + 1}</div>
                ))}
              </div>
              <pre className="code-content">
                <code>{promptFile?.content}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
