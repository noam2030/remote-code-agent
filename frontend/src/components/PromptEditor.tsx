import React, { useState } from 'react'
import type { Project } from '../types'

interface PromptEditorProps {
  selectedProject: Project | null
  isGenerating: boolean
  onSubmit: (prompt: string, projectName?: string) => void
  onCancel?: () => void
}

const CHIPS = [
  {
    label: '✅ Confirm Plan',
    prompt: 'confirm',
  },
  {
    label: '🔀 Merge Pull Request',
    prompt: 'merge',
  },
  {
    label: '🎨 Modernize UI',
    prompt: 'Build a responsive web user interface with a modern dark theme',
  },
  {
    label: '🚀 Deploy Workflows',
    prompt: 'Deploy this application with GitHub Actions workflows for Google Cloud project ai-learning and Vercel noam-projects2',
  },
]

export const PromptEditor: React.FC<PromptEditorProps> = ({
  selectedProject,
  isGenerating,
  onSubmit,
  onCancel,
}) => {
  const [prompt, setPrompt] = useState('')

  const targetName = selectedProject?.name || 'select a project'

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!prompt.trim() || isGenerating) return
    onSubmit(prompt.trim(), selectedProject?.name)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleChipClick = (chipPrompt: string) => {
    if (isGenerating) return
    setPrompt(chipPrompt)
    if (chipPrompt === 'confirm' || chipPrompt === 'merge') {
      onSubmit(chipPrompt, selectedProject?.name)
    }
  }

  return (
    <div className="generator-card">
      <div className="chips-row">
        {CHIPS.map((chip, idx) => (
          <button
            key={idx}
            type="button"
            className="prompt-chip"
            onClick={() => handleChipClick(chip.prompt)}
            disabled={isGenerating}
          >
            {chip.label}
          </button>
        ))}
      </div>

      <textarea
        className="prompt-textarea"
        placeholder="Describe what features, improvements, or bug fixes to implement for this project..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isGenerating}
      />

      <div className="generator-footer">
        <div className="target-reminder">
          Pair-programming workflow for <strong>{targetName}</strong>: plans first, commits to dedicated feature branches, and opens Pull Requests for your review before merging to main.
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {isGenerating && onCancel && (
            <button
              type="button"
              className="btn-cancel"
              onClick={onCancel}
              style={{
                background: '#dc2626',
                color: '#fff',
                border: '1px solid #b91c1c',
                padding: '0.625rem 1.25rem',
                borderRadius: '8px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Stop running execution"
            >
              <span>⏹️ Stop Run</span>
            </button>
          )}
          <button
            type="button"
            className="btn-generate"
            onClick={() => handleSubmit()}
            disabled={isGenerating || !prompt.trim()}
          >
            <span>{isGenerating ? '⏳ Processing...' : '✨ Send Instruction'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
