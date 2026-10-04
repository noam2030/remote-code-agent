import React, { useEffect, useRef, useState } from 'react'

interface TerminalStreamProps {
  logs: string
  isGenerating: boolean
  onClear: () => void
}

const DEFAULT_FONT_SIZE = 16
const MIN_FONT_SIZE = 12
const MAX_FONT_SIZE = 24

export const TerminalStream: React.FC<TerminalStreamProps> = ({
  logs,
  isGenerating,
  onClear,
}) => {
  const terminalEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [copied, setCopied] = useState(false)
  const [fontSize, setFontSize] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('terminal_font_size')
      return saved ? parseInt(saved, 10) || DEFAULT_FONT_SIZE : DEFAULT_FONT_SIZE
    } catch {
      return DEFAULT_FONT_SIZE
    }
  })

  const handleZoomIn = () => {
    setFontSize((prev) => {
      const next = Math.min(MAX_FONT_SIZE, prev + 2)
      try {
        localStorage.setItem('terminal_font_size', next.toString())
      } catch {
        // Ignore storage errors
      }
      return next
    })
  }

  const handleZoomOut = () => {
    setFontSize((prev) => {
      const next = Math.max(MIN_FONT_SIZE, prev - 2)
      try {
        localStorage.setItem('terminal_font_size', next.toString())
      } catch {
        // Ignore storage errors
      }
      return next
    })
  }

  const handleResetZoom = () => {
    setFontSize(DEFAULT_FONT_SIZE)
    try {
      localStorage.setItem('terminal_font_size', DEFAULT_FONT_SIZE.toString())
    } catch {
      // Ignore storage errors
    }
  }

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const handleCopy = () => {
    if (logs) {
      navigator.clipboard.writeText(logs)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="terminal-card">
      <div className="terminal-header">
        <div className="terminal-status">
          <span className={`status-indicator ${isGenerating ? 'active' : ''}`}></span>
          <span className="terminal-title">
            {isGenerating ? '⚡ Agent Execution in Progress...' : '🖥️ Agent Stream Output'}
          </span>
        </div>

        <div className="terminal-controls">
          <div className="terminal-font-controls" title="Adjust console text size">
            <button
              className="btn-font-size"
              onClick={handleZoomOut}
              disabled={fontSize <= MIN_FONT_SIZE}
              title="Decrease font size"
            >
              A-
            </button>
            <span
              className="font-size-label"
              onClick={handleResetZoom}
              title="Click to reset font size to 16px"
              style={{ cursor: 'pointer' }}
            >
              {fontSize}px
            </span>
            <button
              className="btn-font-size"
              onClick={handleZoomIn}
              disabled={fontSize >= MAX_FONT_SIZE}
              title="Increase font size"
            >
              A+
            </button>
          </div>

          <label className="autoscroll-toggle">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            <span>Auto-scroll</span>
          </label>
          {logs && (
            <button className="btn-control" onClick={handleCopy}>
              {copied ? '✅ Copied' : '📋 Copy'}
            </button>
          )}
          {logs && (
            <button className="btn-control" onClick={onClear} disabled={isGenerating}>
              🧹 Clear
            </button>
          )}
        </div>
      </div>

      <div className="terminal-body">
        {logs ? (
          <pre
            className="terminal-text"
            style={{ fontSize: `${fontSize}px`, lineHeight: 1.7 }}
          >
            <code>{logs}</code>
            <div ref={terminalEndRef} />
          </pre>
        ) : (
          <div className="terminal-placeholder">
            <p>Agent streaming thoughts, tool calls, and code creation events will appear here in real time.</p>
          </div>
        )}
      </div>
    </div>
  )
}
