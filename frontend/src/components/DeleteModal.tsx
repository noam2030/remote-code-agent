import React, { useState } from 'react'

interface DeleteModalProps {
  isOpen: boolean
  projectName: string | null
  loading: boolean
  onConfirm: (deleteRemote: boolean) => void
  onCancel: () => void
}

export const DeleteModal: React.FC<DeleteModalProps> = ({
  isOpen,
  projectName,
  loading,
  onConfirm,
  onCancel,
}) => {
  const [deleteRemote, setDeleteRemote] = useState(true)

  if (!isOpen || !projectName) return null

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-container modal-sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title text-danger">⚠️ Delete Project</h3>
          <button className="btn-close" onClick={onCancel} disabled={loading}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <p>
            Are you sure you want to delete project <strong>&quot;{projectName}&quot;</strong>?
          </p>
          <div className="delete-option">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={deleteRemote}
                onChange={(e) => setDeleteRemote(e.target.checked)}
                disabled={loading}
              />
              <span>Also delete from GitHub repository (main branch)</span>
            </label>
          </div>
          <p className="warning-text">This action cannot be undone.</p>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onCancel} disabled={loading}>
            Cancel
          </button>
          <button
            className="btn-danger"
            onClick={() => onConfirm(deleteRemote)}
            disabled={loading}
          >
            {loading ? 'Deleting...' : 'Delete Project'}
          </button>
        </div>
      </div>
    </div>
  )
}
