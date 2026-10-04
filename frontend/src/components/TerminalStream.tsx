import React, { useEffect, useRef, useState } from 'react'

interface TerminalStreamProps {
  logs: string
  isGenerating: boolean
  onClear: () => void
}

export const TerminalStream: React.FC<TerminalStreamProps> = ({
  logs,
  isGenerating,
  onClear,
}) => {
  const terminalEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [copied, setCopied] = useState(false)

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
          <pre className="terminal-text">
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
