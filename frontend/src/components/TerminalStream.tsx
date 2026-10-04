import React, { useEffect, useRef, useState } from 'react'

interface TerminalStreamProps {
  logs: string
  isGenerating: boolean
  onClear: () => void
}

const DEFAULT_FONT_SIZE = 19
const MIN_FONT_SIZE = 13
const MAX_FONT_SIZE = 32

export const TerminalStream: React.FC<TerminalStreamProps> = ({
  logs,
  isGenerating,
  onClear,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)
  const [hasFinishedOnce, setHasFinishedOnce] = useState(false)
  const [fontSize, setFontSize] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('terminal_font_size')
      const parsed = saved ? parseInt(saved, 10) : null
      if (!parsed || parsed <= 16) {
        localStorage.setItem('terminal_font_size', DEFAULT_FONT_SIZE.toString())
        return DEFAULT_FONT_SIZE
      }
      return parsed
    } catch {
      return DEFAULT_FONT_SIZE
    }
  })

  useEffect(() => {
    if (isGenerating) {
      setHasFinishedOnce(true)
    }
  }, [isGenerating])

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [logs])

  const handleZoomIn = () => {
    setFontSize((prev) => {
      const next = Math.min(MAX_FONT_SIZE, prev + 2)
      try {
        localStorage.setItem('terminal_font_size', next.toString())
      } catch {}
      return next
    })
  }

  const handleZoomOut = () => {
    setFontSize((prev) => {
      const next = Math.max(MIN_FONT_SIZE, prev - 2)
      try {
        localStorage.setItem('terminal_font_size', next.toString())
      } catch {}
      return next
    })
  }

  const handleResetZoom = () => {
    setFontSize(DEFAULT_FONT_SIZE)
    try {
      localStorage.setItem('terminal_font_size', DEFAULT_FONT_SIZE.toString())
    } catch {}
  }

  const handleCopy = () => {
    const textToCopy = logs || 'Remote Code Agent ready. Select a project and enter your instructions above to start.'
    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const statusBadge = isGenerating ? (
    <span className="terminal-badge badge-running">RUNNING</span>
  ) : hasFinishedOnce ? (
    <span className="terminal-badge badge-success">SUCCESS</span>
  ) : (
    <span className="terminal-badge badge-idle">IDLE</span>
  )

  return (
    <div className="terminal-card">
      <div className="terminal-header">
        <div className="terminal-title">
          <div className="terminal-lights">
            <span className="t-light t-red"></span>
            <span className="t-light t-yellow"></span>
            <span className="t-light t-green"></span>
          </div>
          <span>Antigravity Live Stream</span>
        </div>

        <div className="terminal-controls">
          {statusBadge}
          <div className="terminal-font-controls" title="Adjust terminal text size">
            <button
              className="terminal-btn"
              onClick={handleZoomOut}
              disabled={fontSize <= MIN_FONT_SIZE}
              title="Decrease font size"
            >
              A-
            </button>
            <span
              className="terminal-size-indicator"
              onClick={handleResetZoom}
              title={`Click to reset font size to ${DEFAULT_FONT_SIZE}px`}
            >
              {fontSize}px
            </span>
            <button
              className="terminal-btn"
              onClick={handleZoomIn}
              disabled={fontSize >= MAX_FONT_SIZE}
              title="Increase font size"
            >
              A+
            </button>
          </div>
          <button className="terminal-btn" onClick={onClear} disabled={isGenerating}>
            Clear
          </button>
          <button className="terminal-btn" onClick={handleCopy}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </div>

      <div
        className="terminal-output"
        ref={terminalRef}
        style={{ fontSize: `${fontSize}px`, lineHeight: 1.75 }}
      >
        {logs ? logs : 'Remote Code Agent ready. Select a project and enter your instructions above to start.'}
      </div>
    </div>
  )
}
