import React, { useEffect, useState } from 'react'
import type { LoadedSkillsResponse } from '../types'

interface SkillsModalProps {
  isOpen: boolean
  skillsData: LoadedSkillsResponse | null
  loading: boolean
  onClose: () => void
  onRefresh?: () => void
}

export const SkillsModal: React.FC<SkillsModalProps> = ({
  isOpen,
  skillsData,
  loading,
  onClose,
  onRefresh,
}) => {
  const [selectedSkill, setSelectedSkill] = useState<string>('')
  const [copied, setCopied] = useState(false)

  const skillNames =
    skillsData?.skill_names || (skillsData?.skills ? Object.keys(skillsData.skills) : [])

  useEffect(() => {
    if (skillNames.length > 0 && (!selectedSkill || !skillNames.includes(selectedSkill))) {
      setSelectedSkill(skillNames[0])
    }
  }, [skillNames, selectedSkill])

  if (!isOpen) return null

  const activeContent = (selectedSkill && skillsData?.skills?.[selectedSkill]) || ''
  const lines = activeContent ? activeContent.split('\n') : []

  const handleCopy = () => {
    if (activeContent) {
      navigator.clipboard.writeText(activeContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="file-modal-header">
          <div className="file-modal-title">
            <span style={{ fontSize: '1.2rem' }}>🧠</span>
            <div style={{ overflow: 'hidden' }}>
              <h3>Loaded Agent Skills</h3>
              <div className="file-modal-path">
                {skillsData?.skills_source ? (
                  <a
                    href={skillsData.skills_source}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#60a5fa', textDecoration: 'none' }}
                  >
                    🔗 {skillsData.skills_source.replace('https://github.com/', '')}
                  </a>
                ) : (
                  'Dynamic remote skills loaded at startup'
                )}
              </div>
            </div>
          </div>
          <div className="file-modal-meta">
            {skillsData && (
              <span className="meta-pill">{skillNames.length} skills loaded</span>
            )}
            {lines.length > 0 && (
              <span className="meta-pill">{lines.length} lines</span>
            )}
            {activeContent && (
              <button
                type="button"
                className="action-btn action-btn-secondary"
                onClick={handleCopy}
                style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
              >
                {copied ? '✅ Copied' : '📋 Copy Skill'}
              </button>
            )}
            {onRefresh && (
              <button
                type="button"
                className="action-btn action-btn-secondary"
                onClick={onRefresh}
                title="Reload skills from backend"
                style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
              >
                🔄 Refresh
              </button>
            )}
            <button
              type="button"
              className="modal-close-btn"
              onClick={onClose}
              title="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {skillNames.length > 0 && (
          <div className="skills-tabs-bar">
            {skillNames.map((name) => (
              <button
                key={name}
                type="button"
                className={`skills-tab-btn ${selectedSkill === name ? 'active' : ''}`}
                onClick={() => setSelectedSkill(name)}
              >
                🛠️ {name}
              </button>
            ))}
          </div>
        )}

        <div className="file-modal-body">
          {loading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-dim)', width: '100%' }}>
              ⏳ Loading dynamic skills...
            </div>
          ) : skillNames.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', width: '100%' }}>
              ⚠️ No loaded skills available.
            </div>
          ) : (
            <div className="code-container">
              <div className="line-numbers">
                {lines.map((_, i) => (
                  <div key={i}>{i + 1}</div>
                ))}
              </div>
              <pre className="code-content">
                <code>{activeContent}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
