import React, { useState } from 'react'
import { getBackendUrl, setBackendUrl } from '../services/api'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: () => void
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onSave }) => {
  const [url, setUrl] = useState(getBackendUrl())

  if (!isOpen) return null

  const handleSave = () => {
    setBackendUrl(url)
    onSave()
    onClose()
  }

  const handleReset = () => {
    setUrl('')
    setBackendUrl('')
    onSave()
    onClose()
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container modal-sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">⚙️ Backend Settings</h3>
          <button className="btn-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <p className="setting-description">
            Configure the Google Cloud Run backend API endpoint for this frontend.
          </p>
          <div className="form-group">
            <label className="input-label">Backend API URL:</label>
            <input
              type="text"
              className="text-input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="e.g. https://remote-code-agent-702552270447.us-central1.run.app"
            />
            <small className="help-text">
              Leave blank to use default (same origin or Vite proxy).
            </small>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={handleReset}>
            Reset Default
          </button>
          <button className="btn-primary" onClick={handleSave}>
            Save Settings
          </button>
        </div>
      </div>
    </div>
  )
}
