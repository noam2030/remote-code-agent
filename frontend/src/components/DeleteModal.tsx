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
      <div className="confirm-modal" onClick={(e) => e.stopPropagation()}>
        <h3>⚠️ Delete Project: {projectName}</h3>

        <p>
          Are you sure you want to delete project <strong>&quot;{projectName}&quot;</strong>?
        </p>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={deleteRemote}
            onChange={(e) => setDeleteRemote(e.target.checked)}
            disabled={loading}
          />
          <span>Also delete from GitHub repository (remote-code-agent-output/main)</span>
        </label>

        <p style={{ color: '#f87171', fontSize: '0.8rem' }}>This action cannot be undone.</p>

        <div className="confirm-modal-actions">
          <button
            type="button"
            className="action-btn action-btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="action-btn action-btn-danger"
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
