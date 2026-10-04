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

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container modal-lg" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="file-icon">📋</span>
            <div>
              <h3 className="modal-title">Master Specification: {promptFile?.project}/prompt.txt</h3>
              <p className="modal-subtitle">
                Canonical consolidated prompt. If used on a blank project, an agent will reproduce this exact application.
              </p>
            </div>
          </div>
          <div className="modal-actions">
            {promptFile?.content && (
              <button className="btn-secondary btn-sm" onClick={handleCopy}>
                {copied ? '✅ Copied' : '📋 Copy Master Prompt'}
              </button>
            )}
            <button className="btn-close" onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="loading-spinner">Loading master prompt...</div>
          ) : (
            <pre className="master-prompt-content">
              <code>{promptFile?.content}</code>
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}
