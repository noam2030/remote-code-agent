import React, { useState } from 'react'
import type { Project } from '../types'

interface PromptEditorProps {
  selectedProject: Project | null
  isGenerating: boolean
  onSubmit: (prompt: string, projectName?: string) => void
}

const QUICK_PROMPTS = [
  'Create a real-time Markdown note taking app with search',
  'Build a Todo List web app with priority filtering and local storage',
  'Build a Currency Exchange Rate converter API with caching',
  'Create a Stock Portfolio tracking dashboard with charts',
]

export const PromptEditor: React.FC<PromptEditorProps> = ({
  selectedProject,
  isGenerating,
  onSubmit,
}) => {
  const [prompt, setPrompt] = useState('')
  const [newProjectName, setNewProjectName] = useState('')

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!prompt.trim() || isGenerating) return
    onSubmit(prompt.trim(), selectedProject ? selectedProject.name : newProjectName.trim() || undefined)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="prompt-editor-card">
      <form onSubmit={handleSubmit}>
        {!selectedProject && (
          <div className="project-name-row">
            <label className="input-label">Project Name (optional):</label>
            <input
              type="text"
              className="text-input"
              placeholder="e.g. currency-converter (auto-derived if left blank)"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              disabled={isGenerating}
            />
          </div>
        )}

        <div className="textarea-wrapper">
          <textarea
            className="prompt-textarea"
            rows={4}
            placeholder={
              selectedProject
                ? `Enter instructions or new features to add to "${selectedProject.name}"...`
                : 'Describe what application or service you want to build...'
            }
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isGenerating}
          />
        </div>

        <div className="prompt-footer">
          <div className="quick-chips">
            <span className="chips-label">Ideas:</span>
            {QUICK_PROMPTS.map((chip, idx) => (
              <button
                key={idx}
                type="button"
                className="chip-btn"
                onClick={() => setPrompt(chip)}
                disabled={isGenerating}
              >
                {chip}
              </button>
            ))}
          </div>

          <button
            type="submit"
            className="btn-submit"
            disabled={isGenerating || !prompt.trim()}
          >
            {isGenerating ? (
              <>
                <span className="spinner"></span> Generating...
              </>
            ) : selectedProject ? (
              `⚡ Update "${selectedProject.name}"`
            ) : (
              '🚀 Generate Application'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
