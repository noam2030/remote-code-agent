import React, { useState } from 'react'
import type { Project } from '../types'

interface PromptEditorProps {
  selectedProject: Project | null
  isGenerating: boolean
  onSubmit: (prompt: string, projectName?: string) => void
}

const CHIPS = [
  {
    label: '🏥 Add Health Check',
    prompt: 'Add a health check endpoint and update OpenAPI documentation',
  },
  {
    label: '🎨 Modernize UI',
    prompt: 'Build a responsive web user interface with a modern dark theme',
  },
  {
    label: '🧪 Add Unit Tests',
    prompt: 'Create comprehensive automated unit tests in tests/ directory',
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

  return (
    <div className="generator-card">
      <div className="card-header-row">
        <h3 className="card-title">⚡ Antigravity CLI on Cloud</h3>
        <div className="correlation-notice">
          <span>📌</span>
          <span>
            Target: <strong>{targetName}</strong>
          </span>
        </div>
      </div>

      <div className="chips-row">
        {CHIPS.map((chip, idx) => (
          <button
            key={idx}
            type="button"
            className="prompt-chip"
            onClick={() => setPrompt(chip.prompt)}
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
          Changes will be committed directly to GitHub repository <strong>{targetName}</strong> on branch{' '}
          <strong>main</strong>.
        </div>
        <button
          type="button"
          className="btn-generate"
          onClick={() => handleSubmit()}
          disabled={isGenerating || !prompt.trim()}
        >
          <span>{isGenerating ? '⏳ Generating...' : '✨ Generate & Push to GitHub'}</span>
        </button>
      </div>
    </div>
  )
}
