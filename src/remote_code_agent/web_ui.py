"""Web Application UI for Remote Code Agent.

Provides a responsive single-page web dashboard to browse projects, select a target project,
and stream autonomous code generation directly to the correlated GitHub directory and Cloud Run.
"""

def get_web_ui_html() -> str:
    """Returns the standalone HTML5/CSS/JavaScript single-page application."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Remote Code Agent - Project Hub</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-main: #0b0f19;
      --bg-card: #111827;
      --bg-card-hover: #1f2937;
      --border-color: #2e384d;
      --border-accent: #3b82f6;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --terminal-bg: #030712;
      --code-font: 'Fira Code', monospace;
      --ui-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--ui-font);
      background-color: var(--bg-main);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Header */
    header {
      background-color: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      padding: 0.85rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand-logo {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      font-weight: bold;
      color: #fff;
      box-shadow: 0 0 16px rgba(59, 130, 246, 0.35);
    }

    .brand-text h1 {
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.01em;
    }

    .brand-text p {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .status-pill {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      background: rgba(16, 185, 129, 0.1);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 0.25rem 0.65rem;
      border-radius: 9999px;
      font-weight: 500;
    }

    .status-dot {
      width: 7px;
      height: 7px;
      background: #10b981;
      border-radius: 50%;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    .nav-btn {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.8rem;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }

    .nav-btn:hover {
      background-color: var(--bg-card-hover);
      color: var(--text-main);
      border-color: #4b5563;
    }

    /* Main Container */
    main {
      flex: 1;
      display: grid;
      grid-template-columns: 360px 1fr;
      height: calc(100vh - 61px);
      overflow: hidden;
    }

    @media (max-width: 900px) {
      main {
        grid-template-columns: 1fr;
        height: auto;
        overflow: visible;
      }
    }

    /* Left Sidebar: Projects List */
    .sidebar {
      background-color: #0d121f;
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .sidebar-header {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .sidebar-title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.95rem;
      font-weight: 600;
    }

    .count-badge {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      font-size: 0.7rem;
      padding: 0.1rem 0.45rem;
      border-radius: 9999px;
    }

    .sidebar-actions {
      display: flex;
      gap: 0.4rem;
    }

    .icon-btn {
      background: transparent;
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      border-radius: 6px;
      padding: 0.3rem 0.5rem;
      cursor: pointer;
      font-size: 0.8rem;
      transition: all 0.15s;
    }

    .icon-btn:hover {
      background: var(--bg-card-hover);
      color: var(--text-main);
    }

    .create-project-box {
      padding: 0.75rem 1.25rem;
      background: rgba(17, 24, 39, 0.6);
      border-bottom: 1px solid var(--border-color);
    }

    .create-input-group {
      display: flex;
      gap: 0.5rem;
    }

    .create-input {
      flex: 1;
      background: var(--bg-main);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.45rem 0.65rem;
      border-radius: 6px;
      font-size: 0.8rem;
      outline: none;
    }

    .create-input:focus {
      border-color: var(--primary);
    }

    .btn-create {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.45rem 0.8rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn-create:hover {
      background: var(--primary-hover);
    }

    .search-box {
      padding: 0.75rem 1.25rem;
      border-bottom: 1px solid var(--border-color);
    }

    .search-input {
      width: 100%;
      background: var(--bg-main);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.45rem 0.75rem;
      border-radius: 6px;
      font-size: 0.8rem;
      outline: none;
    }

    .search-input:focus {
      border-color: var(--primary);
    }

    .project-list {
      flex: 1;
      overflow-y: auto;
      padding: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .project-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 0.85rem;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .project-card:hover {
      border-color: #4b5563;
      background: var(--bg-card-hover);
    }

    .project-card.active {
      border-color: var(--border-accent);
      background: rgba(59, 130, 246, 0.08);
      box-shadow: 0 0 0 1px var(--primary);
    }

    .project-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .project-card-title {
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 0.4rem;
      word-break: break-all;
    }

    .active-tag {
      font-size: 0.65rem;
      background: var(--primary);
      color: #fff;
      padding: 0.1rem 0.35rem;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
    }

    .project-links {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      align-items: center;
    }

    .project-tag {
      font-size: 0.7rem;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      font-weight: 500;
    }

    .tag-live {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .tag-live:hover {
      background: rgba(16, 185, 129, 0.25);
    }

    .tag-github {
      background: rgba(147, 197, 253, 0.1);
      color: #93c5fd;
      border: 1px solid rgba(147, 197, 253, 0.2);
    }
    .tag-github:hover {
      background: rgba(147, 197, 253, 0.2);
    }

    .tag-files {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-dim);
    }

    .tag-loc {
      background: rgba(139, 92, 246, 0.12);
      color: #c4b5fd;
      border: 1px solid rgba(139, 92, 246, 0.25);
    }

    .tag-tokens {
      background: rgba(245, 158, 11, 0.12);
      color: #fcd34d;
      border: 1px solid rgba(245, 158, 11, 0.25);
    }

    /* Right Content Area */
    .content-area {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
      padding: 1.5rem;
      gap: 1.5rem;
    }

    /* Active Project Banner */
    .active-project-banner {
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .banner-title {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .banner-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
    }

    .banner-name {
      font-size: 1.35rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .banner-stats-row {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      flex-wrap: wrap;
      margin-top: 0.35rem;
    }

    .banner-stat-pill {
      background: rgba(15, 23, 42, 0.75);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 0.25rem 0.55rem;
      font-size: 0.75rem;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }

    .banner-stat-pill .stat-icon {
      font-size: 0.85rem;
    }

    .banner-stat-pill .stat-label {
      color: var(--text-muted);
    }

    .banner-stat-pill .stat-val {
      color: #fff;
      font-weight: 600;
    }

    .banner-actions {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
    }

    .action-btn {
      padding: 0.5rem 0.9rem;
      font-size: 0.8rem;
      border-radius: 6px;
      font-weight: 500;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      cursor: pointer;
      transition: all 0.15s ease;
      border: 1px solid transparent;
    }

    .action-btn-primary {
      background: #10b981;
      color: #fff;
    }
    .action-btn-primary:hover {
      background: #059669;
    }

    .action-btn-secondary {
      background: var(--bg-card);
      border-color: var(--border-color);
      color: var(--text-main);
    }
    .action-btn-secondary:hover {
      background: var(--bg-card-hover);
      border-color: #4b5563;
    }

    .action-btn-danger {
      background: rgba(239, 68, 68, 0.12);
      border-color: rgba(239, 68, 68, 0.3);
      color: #fca5a5;
    }
    .action-btn-danger:hover {
      background: rgba(239, 68, 68, 0.25);
      border-color: #ef4444;
      color: #fff;
    }

    .btn-card-delete {
      background: transparent;
      border: none;
      color: var(--text-dim);
      font-size: 0.8rem;
      cursor: pointer;
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      transition: all 0.15s;
    }
    .btn-card-delete:hover {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }

    /* Files Viewer Drawer */
    .files-panel {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .files-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.85rem;
      font-weight: 600;
    }

    .files-list {
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      max-height: 240px;
      overflow-y: auto;
    }

    .file-item-card {
      background: var(--bg-main);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 0.45rem 0.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      transition: all 0.15s ease;
      text-decoration: none;
    }

    .file-item-card:hover {
      background: var(--bg-card-hover);
      border-color: var(--primary);
      transform: translateX(2px);
    }

    .file-item-main {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      overflow: hidden;
    }

    .file-item-path {
      font-family: var(--code-font);
      font-size: 0.8rem;
      color: var(--text-main);
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }

    .file-item-meta {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-shrink: 0;
    }

    .file-pill {
      font-size: 0.7rem;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-dim);
    }

    .file-pill-loc {
      color: #c4b5fd;
      background: rgba(139, 92, 246, 0.1);
    }

    .file-item-btn {
      font-size: 0.72rem;
      color: #60a5fa;
      font-weight: 500;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.2);
    }

    /* File Viewer Modal */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(3, 7, 18, 0.82);
      backdrop-filter: blur(8px);
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }

    .file-modal {
      width: 90vw;
      max-width: 1050px;
      height: 82vh;
      max-height: 880px;
      background: #0e1526;
      border: 1px solid var(--border-color);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75);
    }

    .file-modal-header {
      padding: 0.85rem 1.25rem;
      background: #111827;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }

    .file-modal-title {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      overflow: hidden;
    }

    .file-modal-title h3 {
      font-size: 0.95rem;
      font-weight: 600;
      color: #fff;
    }

    .file-modal-path {
      font-family: var(--code-font);
      font-size: 0.75rem;
      color: var(--text-dim);
    }

    .file-modal-meta {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-shrink: 0;
    }

    .meta-pill {
      font-size: 0.72rem;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-muted);
      font-family: var(--code-font);
    }

    .modal-close-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 1.2rem;
      cursor: pointer;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      transition: all 0.15s;
    }

    .modal-close-btn:hover {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }

    .file-modal-body {
      flex: 1;
      display: flex;
      overflow: hidden;
      background: #030712;
      position: relative;
    }

    .code-container {
      display: flex;
      flex: 1;
      overflow: auto;
      font-family: var(--code-font);
      font-size: 0.82rem;
    }

    .line-numbers {
      padding: 1rem 0.65rem;
      text-align: right;
      color: #4b5563;
      user-select: none;
      border-right: 1px solid #1f2937;
      background: #090d16;
      font-size: 0.78rem;
      line-height: 1.5;
      min-width: 48px;
    }

    .code-content {
      padding: 1rem 1.25rem;
      margin: 0;
      color: #e2e8f0;
      line-height: 1.5;
      white-space: pre;
      overflow-x: auto;
      flex: 1;
    }

    /* Generator Section */
    .generator-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .card-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 600;
    }

    .correlation-notice {
      font-size: 0.8rem;
      color: #60a5fa;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.2);
      padding: 0.5rem 0.8rem;
      border-radius: 6px;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .chips-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }

    .prompt-chip {
      background: var(--bg-main);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      font-size: 0.75rem;
      padding: 0.35rem 0.65rem;
      border-radius: 9999px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .prompt-chip:hover {
      background: var(--bg-card-hover);
      color: var(--text-main);
      border-color: var(--primary);
    }

    .prompt-textarea {
      width: 100%;
      min-height: 110px;
      background: var(--bg-main);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.85rem;
      border-radius: 8px;
      font-size: 0.9rem;
      font-family: inherit;
      resize: vertical;
      outline: none;
      line-height: 1.5;
    }

    .prompt-textarea:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }

    .generator-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .target-reminder {
      font-size: 0.8rem;
      color: var(--text-dim);
    }

    .target-reminder strong {
      color: #93c5fd;
    }

    .btn-generate {
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: white;
      border: none;
      padding: 0.65rem 1.4rem;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
      transition: all 0.15s ease;
    }

    .btn-generate:hover:not(:disabled) {
      background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
      transform: translateY(-1px);
    }

    .btn-generate:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }

    /* Terminal Console */
    .terminal-card {
      background: var(--terminal-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }

    .terminal-header {
      background: #0f172a;
      border-bottom: 1px solid var(--border-color);
      padding: 0.6rem 1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .terminal-title {
      font-size: 0.8rem;
      font-family: var(--code-font);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .terminal-lights {
      display: flex;
      gap: 0.35rem;
    }

    .t-light {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .t-red { background: #ef4444; }
    .t-yellow { background: #f59e0b; }
    .t-green { background: #10b981; }

    .terminal-controls {
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }

    .terminal-badge {
      font-size: 0.7rem;
      font-family: var(--code-font);
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      font-weight: 500;
    }

    .badge-idle { background: #1f2937; color: #9ca3af; }
    .badge-running { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #3b82f6; }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }

    .terminal-btn {
      background: transparent;
      border: 1px solid #334155;
      color: var(--text-dim);
      font-size: 0.7rem;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      cursor: pointer;
    }
    .terminal-btn:hover {
      color: var(--text-main);
      border-color: #64748b;
    }

    .terminal-output {
      padding: 1rem;
      font-family: var(--code-font);
      font-size: 0.82rem;
      line-height: 1.6;
      color: #e2e8f0;
      height: 280px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .chunk-thought {
      color: #c084fc;
      font-style: italic;
    }

    .chunk-tool {
      color: #fbbf24;
      font-weight: 500;
    }

    .chunk-success {
      color: #34d399;
      font-weight: 600;
    }

    /* Notification Banner */
    .success-alert {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 8px;
      padding: 1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .success-left {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .success-icon {
      font-size: 1.5rem;
    }

    .success-text h4 {
      font-size: 0.9rem;
      color: #34d399;
    }

    .success-text p {
      font-size: 0.75rem;
      color: var(--text-muted);
    }
  </style>
</head>
<body>

  <!-- Top Bar -->
  <header>
    <div class="brand">
      <div class="brand-logo">⚡</div>
      <div class="brand-text">
        <h1>Remote Code Agent</h1>
        <p>Google Antigravity Agent Service • Cloud Run & GitHub Continuous Deployment</p>
      </div>
    </div>
    <div class="header-actions">
      <div class="status-pill">
        <span class="status-dot"></span>
        <span>Connected to Agent</span>
      </div>
      <a href="https://github.com/noam2030/remote-code-agent-output" target="_blank" rel="noopener" class="nav-btn">
        🐙 GitHub Central Repo
      </a>
      <a href="/docs" target="_blank" rel="noopener" class="nav-btn">
        📖 API Docs
      </a>
    </div>
  </header>

  <!-- Main Grid -->
  <main>
    <!-- Left Sidebar: Project Explorer -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="sidebar-title">
          <span>📁 Projects</span>
          <span class="count-badge" id="projectCount">0</span>
        </div>
        <div class="sidebar-actions">
          <button class="icon-btn" id="btnRefresh" title="Refresh project list">🔄</button>
          <button class="icon-btn" id="btnToggleNew" title="Create new project">+ New</button>
        </div>
      </div>

      <!-- Quick New Project Input (Hidden by default) -->
      <div class="create-project-box" id="newProjectBox" style="display: none;">
        <div class="create-input-group">
          <input type="text" id="newProjectInput" class="create-input" placeholder="project-name (e.g. todo-app)" />
          <button class="btn-create" id="btnConfirmCreate">Create</button>
        </div>
      </div>

      <!-- Search Filter -->
      <div class="search-box">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search projects..." />
      </div>

      <!-- Project Cards List -->
      <div class="project-list" id="projectList">
        <div style="padding: 1.5rem; text-align: center; color: var(--text-dim); font-size: 0.85rem;">
          Loading projects...
        </div>
      </div>
    </aside>

    <!-- Right Workspace Area -->
    <section class="content-area">

      <!-- Active Project Banner -->
      <div class="active-project-banner" id="activeProjectBanner">
        <div class="banner-title">
          <span class="banner-sub">Target Project</span>
          <h2 class="banner-name" id="bannerProjectName">Select a project</h2>
          <div class="banner-stats-row" id="bannerStatsRow" style="display: none;">
            <div class="banner-stat-pill" title="Total Lines of Code">
              <span class="stat-icon">📝</span>
              <span class="stat-label">Code:</span>
              <strong class="stat-val" id="bannerLocVal">0 LOC</strong>
            </div>
            <div class="banner-stat-pill" title="Tokens Spent Building Project">
              <span class="stat-icon">🪙</span>
              <span class="stat-label">Tokens Spent:</span>
              <strong class="stat-val" id="bannerTokensVal">0</strong>
            </div>
            <div class="banner-stat-pill" title="Total Project Files">
              <span class="stat-icon">📂</span>
              <span class="stat-label">Files:</span>
              <strong class="stat-val" id="bannerFilesVal">0</strong>
            </div>
          </div>
        </div>
        <div class="banner-actions">
          <a id="bannerLiveLink" href="#" target="_blank" class="action-btn action-btn-primary" style="display: none;">
            🚀 Open Live Cloud Run App
          </a>
          <a id="bannerGithubLink" href="#" target="_blank" class="action-btn action-btn-secondary" style="display: none;">
            🐙 View on GitHub
          </a>
          <button id="btnToggleFiles" class="action-btn action-btn-secondary">
            📂 Project Files (<span id="bannerFileCount">0</span>)
          </button>
          <button id="btnDeleteProject" class="action-btn action-btn-danger" style="display: none;">
            🗑️ Delete Project
          </button>
        </div>
      </div>

      <!-- Files Drawer (Toggleable) -->
      <div class="files-panel" id="filesPanel" style="display: none;">
        <div class="files-header">
          <span>Files in this project <span style="font-size: 0.72rem; color: var(--text-dim); font-weight: normal; margin-left: 0.4rem;">(Click to view content)</span></span>
          <span id="filesStatusText" style="color: var(--text-dim); font-size: 0.75rem;">Synced with workspace</span>
        </div>
        <div class="files-list" id="filesList">
          <span style="font-size: 0.75rem; color: var(--text-dim);">No files yet.</span>
        </div>
      </div>

      <!-- Success Notification Alert (Hidden until generation completes) -->
      <div class="success-alert" id="successAlert" style="display: none;">
        <div class="success-left">
          <span class="success-icon">🎉</span>
          <div class="success-text">
            <h4 id="alertTitle">Code generated and pushed directly to GitHub!</h4>
            <p id="alertSub">GitHub Actions is automatically building and deploying to Google Cloud Run.</p>
          </div>
        </div>
        <div>
          <a id="alertLink" href="#" target="_blank" class="action-btn action-btn-secondary" style="font-size: 0.75rem;">
            View in GitHub →
          </a>
        </div>
      </div>

      <!-- Generator Section -->
      <div class="generator-card">
        <div class="card-header-row">
          <h3 class="card-title">✨ Autonomous Code Generation</h3>
          <div class="correlation-notice">
            <span>📌</span>
            <span>Target: <strong id="noticeTargetName">select a project</strong></span>
          </div>
        </div>

        <!-- Quick Prompt Suggestions -->
        <div class="chips-row">
          <button class="prompt-chip" data-prompt="Add a health check endpoint and update OpenAPI documentation">
            🏥 Add Health Check
          </button>
          <button class="prompt-chip" data-prompt="Build a responsive web user interface with a modern dark theme">
            🎨 Modernize UI
          </button>
          <button class="prompt-chip" data-prompt="Create comprehensive automated unit tests in tests/ directory">
            🧪 Add Unit Tests
          </button>
          <button class="prompt-chip" data-prompt="Add a Dockerfile and configure for Google Cloud Run on port $PORT">
            🐳 Cloud Run Setup
          </button>
        </div>

        <textarea
          id="promptInput"
          class="prompt-textarea"
          placeholder="Describe what features, improvements, or bug fixes to implement for this project..."
        ></textarea>

        <div class="generator-footer">
          <div class="target-reminder">
            Changes will be committed directly to <strong id="footerTargetName">workspace</strong> on GitHub branch <strong>main</strong>.
          </div>
          <button id="btnGenerate" class="btn-generate">
            <span>✨ Generate & Push to GitHub</span>
          </button>
        </div>
      </div>

      <!-- Live Terminal Streaming Console -->
      <div class="terminal-card">
        <div class="terminal-header">
          <div class="terminal-title">
            <div class="terminal-lights">
              <span class="t-light t-red"></span>
              <span class="t-light t-yellow"></span>
              <span class="t-light t-green"></span>
            </div>
            <span>Antigravity Live Stream</span>
          </div>
          <div class="terminal-controls">
            <span class="terminal-badge badge-idle" id="streamStatus">IDLE</span>
            <button class="terminal-btn" id="btnClearTerminal">Clear</button>
            <button class="terminal-btn" id="btnCopyTerminal">Copy</button>
          </div>
        </div>
        <div class="terminal-output" id="terminalOutput">Remote Code Agent ready. Select a project and enter your instructions above to start.</div>
      </div>

    </section>
  </main>

  <!-- File Viewer Modal -->
  <div class="modal-backdrop" id="fileModalBackdrop" style="display: none;">
    <div class="file-modal" id="fileModal">
      <div class="file-modal-header">
        <div class="file-modal-title">
          <span class="file-modal-icon" style="font-size: 1.1rem;">📄</span>
          <div style="overflow: hidden;">
            <h3 id="modalFileName">file.py</h3>
            <div class="file-modal-path" id="modalFilePath">path/to/file.py</div>
          </div>
        </div>
        <div class="file-modal-meta">
          <span class="meta-pill" id="modalFileLanguage">CODE</span>
          <span class="meta-pill" id="modalFileLines">0 lines</span>
          <span class="meta-pill" id="modalFileSize">0 B</span>
          <button class="action-btn action-btn-secondary" id="btnCopyFile" style="font-size: 0.75rem; padding: 0.25rem 0.6rem;">📋 Copy</button>
          <button class="modal-close-btn" id="btnCloseModal" title="Close (Esc)">✕</button>
        </div>
      </div>
      <div class="file-modal-body">
        <div id="modalLoading" style="display: none; padding: 3rem; text-align: center; color: var(--text-dim); width: 100%;">
          <span>⏳ Loading file content...</span>
        </div>
        <div id="modalError" style="display: none; padding: 2rem; color: #fca5a5; width: 100%;"></div>
        <div id="modalBinaryNotice" style="display: none; padding: 3rem; text-align: center; color: var(--text-muted); width: 100%;">
          <p>📦 This is a binary file and cannot be previewed directly as text.</p>
        </div>
        <div class="code-container" id="modalCodeContainer" style="display: none;">
          <div class="line-numbers" id="modalLineNumbers"></div>
          <pre class="code-content"><code id="modalCodeContent"></code></pre>
        </div>
      </div>
    </div>
  </div>

  <!-- Client JavaScript Logic -->
  <script>
    let projects = [];
    let selectedProject = null;
    let isGenerating = false;
    let currentModalFileContent = '';

    // Elements
    const projectListEl = document.getElementById('projectList');
    const projectCountEl = document.getElementById('projectCount');
    const btnRefresh = document.getElementById('btnRefresh');
    const btnToggleNew = document.getElementById('btnToggleNew');
    const newProjectBox = document.getElementById('newProjectBox');
    const newProjectInput = document.getElementById('newProjectInput');
    const btnConfirmCreate = document.getElementById('btnConfirmCreate');
    const searchInput = document.getElementById('searchInput');

    const bannerProjectName = document.getElementById('bannerProjectName');
    const bannerLiveLink = document.getElementById('bannerLiveLink');
    const bannerGithubLink = document.getElementById('bannerGithubLink');
    const bannerFileCount = document.getElementById('bannerFileCount');
    const bannerStatsRow = document.getElementById('bannerStatsRow');
    const bannerLocVal = document.getElementById('bannerLocVal');
    const bannerTokensVal = document.getElementById('bannerTokensVal');
    const bannerFilesVal = document.getElementById('bannerFilesVal');
    const btnToggleFiles = document.getElementById('btnToggleFiles');
    const btnDeleteProject = document.getElementById('btnDeleteProject');
    const filesPanel = document.getElementById('filesPanel');
    const filesListEl = document.getElementById('filesList');

    const noticeTargetName = document.getElementById('noticeTargetName');
    const footerTargetName = document.getElementById('footerTargetName');
    const promptInput = document.getElementById('promptInput');
    const btnGenerate = document.getElementById('btnGenerate');

    const terminalOutput = document.getElementById('terminalOutput');
    const streamStatus = document.getElementById('streamStatus');
    const btnClearTerminal = document.getElementById('btnClearTerminal');
    const btnCopyTerminal = document.getElementById('btnCopyTerminal');
    const successAlert = document.getElementById('successAlert');
    const alertLink = document.getElementById('alertLink');

    // Modal elements
    const fileModalBackdrop = document.getElementById('fileModalBackdrop');
    const modalFileName = document.getElementById('modalFileName');
    const modalFilePath = document.getElementById('modalFilePath');
    const modalFileLanguage = document.getElementById('modalFileLanguage');
    const modalFileLines = document.getElementById('modalFileLines');
    const modalFileSize = document.getElementById('modalFileSize');
    const btnCopyFile = document.getElementById('btnCopyFile');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const modalLoading = document.getElementById('modalLoading');
    const modalError = document.getElementById('modalError');
    const modalBinaryNotice = document.getElementById('modalBinaryNotice');
    const modalCodeContainer = document.getElementById('modalCodeContainer');
    const modalLineNumbers = document.getElementById('modalLineNumbers');
    const modalCodeContent = document.getElementById('modalCodeContent');

    function formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function escapeHtml(text) {
      if (!text) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // Fetch and render projects
    async function loadProjects(preferredName = null) {
      try {
        const res = await fetch('/api/projects');
        if (!res.ok) throw new Error('Failed to fetch projects');
        projects = await res.json();
        projectCountEl.textContent = projects.length;
        renderProjectsList();

        // Select preferred or first project
        if (preferredName) {
          const match = projects.find(p => p.name === preferredName);
          if (match) selectProject(match);
        } else if (!selectedProject && projects.length > 0) {
          selectProject(projects[0]);
        }
      } catch (err) {
        console.error('Error loading projects:', err);
        projectListEl.innerHTML = `<div style="padding: 1rem; color: #ef4444; font-size: 0.8rem;">Failed to load projects: ${err.message}</div>`;
      }
    }

    function renderProjectsList() {
      const query = searchInput.value.toLowerCase().trim();
      const filtered = projects.filter(p => p.name.toLowerCase().includes(query));

      if (filtered.length === 0) {
        projectListEl.innerHTML = '<div style="padding: 1.5rem; text-align: center; color: var(--text-dim); font-size: 0.8rem;">No matching projects found.</div>';
        return;
      }

      projectListEl.innerHTML = filtered.map(p => {
        const isActive = selectedProject && selectedProject.name === p.name;
        const loc = p.lines_of_code || 0;
        const tokens = p.tokens_spent || 0;
        return `
          <div class="project-card ${isActive ? 'active' : ''}" data-name="${escapeHtml(p.name)}">
            <div class="project-card-header">
              <span class="project-card-title">
                📁 ${escapeHtml(p.name)}
              </span>
              <div style="display: flex; align-items: center; gap: 0.35rem;">
                ${isActive ? '<span class="active-tag">Active</span>' : ''}
                <button class="btn-card-delete" title="Delete project" onclick="event.stopPropagation(); requestDeleteProject('${escapeHtml(p.name)}')">🗑️</button>
              </div>
            </div>
            <div class="project-links">
              ${p.cloud_run_url ? `
                <a href="${p.cloud_run_url}" target="_blank" class="project-tag tag-live" onclick="event.stopPropagation()">
                  🚀 Live App
                </a>
              ` : ''}
              ${p.github_url ? `
                <a href="${p.github_url}" target="_blank" class="project-tag tag-github" onclick="event.stopPropagation()">
                  🐙 GitHub
                </a>
              ` : ''}
              <span class="project-tag tag-files" title="${p.files_count || 0} files">
                📄 ${p.files_count || 0} files
              </span>
              <span class="project-tag tag-loc" title="${loc.toLocaleString()} lines of code">
                📝 ${loc.toLocaleString()} LOC
              </span>
              <span class="project-tag tag-tokens" title="${tokens.toLocaleString()} tokens spent building">
                🪙 ${tokens.toLocaleString()}
              </span>
            </div>
          </div>
        `;
      }).join('');

      // Add click listeners
      projectListEl.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('click', () => {
          const name = card.getAttribute('data-name');
          const p = projects.find(item => item.name === name);
          if (p) selectProject(p);
        });
      });
    }

    // Select a project
    async function selectProject(p) {
      selectedProject = p;
      bannerProjectName.textContent = p.name;
      noticeTargetName.textContent = p.name;
      footerTargetName.textContent = `${p.name}/`;

      bannerStatsRow.style.display = 'flex';
      bannerLocVal.textContent = `${(p.lines_of_code || 0).toLocaleString()} LOC`;
      bannerTokensVal.textContent = (p.tokens_spent || 0).toLocaleString();
      bannerFilesVal.textContent = (p.files_count || 0);

      if (p.cloud_run_url) {
        bannerLiveLink.href = p.cloud_run_url;
        bannerLiveLink.style.display = 'inline-flex';
      } else {
        bannerLiveLink.style.display = 'none';
      }

      if (p.github_url) {
        bannerGithubLink.href = p.github_url;
        bannerGithubLink.style.display = 'inline-flex';
      } else {
        bannerGithubLink.style.display = 'none';
      }

      btnDeleteProject.style.display = 'inline-flex';

      renderProjectsList();

      // Fetch detailed files and stats for this project
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(p.name)}`);
        if (res.ok) {
          const details = await res.json();
          p.files = details.files || [];
          p.files_count = details.files_count || 0;
          p.files_detail = details.files_detail || [];
          p.lines_of_code = details.lines_of_code || 0;
          p.tokens_spent = details.tokens_spent || 0;
          p.stats = details.stats || {};

          bannerFileCount.textContent = p.files_count;
          bannerFilesVal.textContent = p.files_count;
          bannerLocVal.textContent = `${p.lines_of_code.toLocaleString()} LOC`;
          bannerTokensVal.textContent = p.tokens_spent.toLocaleString();

          renderFiles(p.name, p.files_detail);
          renderProjectsList();
        }
      } catch (e) {
        console.error('Error fetching project details:', e);
      }
    }

    function renderFiles(projectName, filesDetail) {
      if (!filesDetail || filesDetail.length === 0) {
        filesListEl.innerHTML = '<span style="font-size: 0.75rem; color: var(--text-dim); padding: 0.5rem;">No files found in workspace.</span>';
        return;
      }
      filesListEl.innerHTML = filesDetail.map(f => {
        const path = typeof f === 'string' ? f : f.path;
        const lines = f.lines !== undefined ? f.lines : 0;
        const sizeBytes = f.size_bytes || 0;
        const isBin = f.is_binary || false;

        return `
          <div class="file-item-card" data-proj="${escapeHtml(projectName)}" data-file="${escapeHtml(path)}">
            <div class="file-item-main">
              <span style="font-size: 0.85rem;">${isBin ? '📦' : '📄'}</span>
              <span class="file-item-path" title="${escapeHtml(path)}">${escapeHtml(path)}</span>
            </div>
            <div class="file-item-meta">
              <span class="file-pill file-pill-loc">${isBin ? 'binary' : lines.toLocaleString() + ' lines'}</span>
              <span class="file-pill file-pill-size">${formatBytes(sizeBytes)}</span>
              <span class="file-item-btn">View 👁️</span>
            </div>
          </div>
        `;
      }).join('');

      filesListEl.querySelectorAll('.file-item-card').forEach(card => {
        card.addEventListener('click', () => {
          const proj = card.getAttribute('data-proj');
          const file = card.getAttribute('data-file');
          openFileViewer(proj, file);
        });
      });
    }

    // File Viewer Modal Logic
    async function openFileViewer(projectName, filePath) {
      if (!projectName || !filePath) return;

      fileModalBackdrop.style.display = 'flex';
      modalFileName.textContent = filePath.split('/').pop();
      modalFilePath.textContent = `${projectName}/${filePath}`;
      modalLoading.style.display = 'block';
      modalError.style.display = 'none';
      modalBinaryNotice.style.display = 'none';
      modalCodeContainer.style.display = 'none';
      btnCopyFile.disabled = true;

      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}/files/${encodeURIComponent(filePath)}`);
        if (!res.ok) {
          const errData = await res.json().catch(() => ({ detail: 'Failed to read file' }));
          throw new Error(errData.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        modalLoading.style.display = 'none';

        const ext = data.extension || '';
        modalFileLanguage.textContent = ext ? ext.replace('.', '').toUpperCase() : 'TEXT';
        modalFileSize.textContent = formatBytes(data.size_bytes);

        if (data.is_binary) {
          modalFileLines.textContent = 'Binary';
          modalBinaryNotice.style.display = 'block';
          return;
        }

        modalFileLines.textContent = `${data.lines.toLocaleString()} lines`;
        currentModalFileContent = data.content || '';
        btnCopyFile.disabled = false;

        // Render line numbers and code content
        const linesCount = data.lines || 1;
        modalLineNumbers.innerHTML = Array.from({ length: linesCount }, (_, i) => i + 1).join('<br>');
        modalCodeContent.textContent = data.content || '';
        modalCodeContainer.style.display = 'flex';

      } catch (err) {
        modalLoading.style.display = 'none';
        modalError.textContent = `Error loading file: ${err.message}`;
        modalError.style.display = 'block';
      }
    }

    function closeFileViewer() {
      fileModalBackdrop.style.display = 'none';
      modalCodeContent.textContent = '';
      modalLineNumbers.innerHTML = '';
      currentModalFileContent = '';
    }

    btnCloseModal.addEventListener('click', closeFileViewer);
    fileModalBackdrop.addEventListener('click', (e) => {
      if (e.target === fileModalBackdrop) closeFileViewer();
    });
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && fileModalBackdrop.style.display !== 'none') {
        closeFileViewer();
      }
    });

    btnCopyFile.addEventListener('click', () => {
      if (!currentModalFileContent) return;
      navigator.clipboard.writeText(currentModalFileContent);
      const prevText = btnCopyFile.textContent;
      btnCopyFile.textContent = '✓ Copied!';
      setTimeout(() => { btnCopyFile.textContent = prevText; }, 1500);
    });

    // Create New Project
    function createNewProject() {
      const rawName = newProjectInput.value.trim();
      if (!rawName) return;
      const cleanName = rawName.toLowerCase().replace(/[\s_]+/g, '-').replace(/[^a-z0-9\-]/g, '').replace(/\-+/g, '-').replace(/^\-|\-$/g, '') || 'new-app';

      const existing = projects.find(p => p.name === cleanName);
      if (existing) {
        selectProject(existing);
        newProjectBox.style.display = 'none';
        newProjectInput.value = '';
        return;
      }

      const newProj = {
        name: cleanName,
        github_url: `https://github.com/noam2030/remote-code-agent-output/tree/main/${cleanName}`,
        cloud_run_url: null,
        files: [],
        files_count: 0,
        is_local: true,
        has_remote: false,
      };

      projects.unshift(newProj);
      projectCountEl.textContent = projects.length;
      selectProject(newProj);

      newProjectBox.style.display = 'none';
      newProjectInput.value = '';
    }

    // Event Handlers
    btnRefresh.addEventListener('click', () => loadProjects(selectedProject ? selectedProject.name : null));
    btnToggleNew.addEventListener('click', () => {
      newProjectBox.style.display = newProjectBox.style.display === 'none' ? 'block' : 'none';
      if (newProjectBox.style.display === 'block') newProjectInput.focus();
    });
    btnConfirmCreate.addEventListener('click', createNewProject);
    newProjectInput.addEventListener('keydown', e => { if (e.key === 'Enter') createNewProject(); });
    searchInput.addEventListener('input', renderProjectsList);

    btnToggleFiles.addEventListener('click', () => {
      filesPanel.style.display = filesPanel.style.display === 'none' ? 'flex' : 'none';
    });

    document.querySelectorAll('.prompt-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        promptInput.value = chip.getAttribute('data-prompt');
        promptInput.focus();
      });
    });

    btnClearTerminal.addEventListener('click', () => {
      terminalOutput.textContent = '';
    });

    btnCopyTerminal.addEventListener('click', () => {
      navigator.clipboard.writeText(terminalOutput.textContent);
      const originalText = btnCopyTerminal.textContent;
      btnCopyTerminal.textContent = 'Copied!';
      setTimeout(() => { btnCopyTerminal.textContent = originalText; }, 1500);
    });

    // Delete Project Request
    async function requestDeleteProject(name) {
      if (!name) return;
      const confirmed = confirm(
        `Are you sure you want to delete project "${name}"?\\n\\n` +
        `This will permanently remove the project from both your local workspace and the GitHub repository.`
      );
      if (!confirmed) return;

      terminalOutput.textContent += `\\n🗑️ [Delete] Deleting project "${name}" from local workspace and GitHub...\\n`;
      terminalOutput.scrollTop = terminalOutput.scrollHeight;

      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(name)}?delete_remote=true`, {
          method: 'DELETE',
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Failed to delete project');
        }

        terminalOutput.textContent += `✅ [Delete] ${data.message}\\n`;
        terminalOutput.scrollTop = terminalOutput.scrollHeight;

        if (selectedProject && selectedProject.name === name) {
          selectedProject = null;
        }

        await loadProjects();

        if (projects.length === 0) {
          bannerProjectName.textContent = 'No projects';
          noticeTargetName.textContent = 'create or select a project';
          footerTargetName.textContent = 'workspace';
          bannerLiveLink.style.display = 'none';
          bannerGithubLink.style.display = 'none';
          btnDeleteProject.style.display = 'none';
          bannerFileCount.textContent = '0';
          bannerStatsRow.style.display = 'none';
          filesListEl.innerHTML = '<span style="font-size: 0.75rem; color: var(--text-dim);">No files found.</span>';
        }
      } catch (err) {
        console.error('Delete error:', err);
        terminalOutput.textContent += `❌ [Delete Error] ${err.message}\\n`;
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
        alert(`Failed to delete project "${name}": ${err.message}`);
      }
    }

    btnDeleteProject.addEventListener('click', () => {
      if (selectedProject) {
        requestDeleteProject(selectedProject.name);
      }
    });

    // Execute Generation Stream
    async function startGeneration() {
      if (isGenerating) return;
      if (!selectedProject) {
        alert('Please select or create a project first.');
        return;
      }
      const prompt = promptInput.value.trim();
      if (!prompt) {
        alert('Please enter instructions for the code agent.');
        promptInput.focus();
        return;
      }

      isGenerating = true;
      btnGenerate.disabled = true;
      btnGenerate.innerHTML = '<span>⏳ Generating Code...</span>';
      streamStatus.className = 'terminal-badge badge-running';
      streamStatus.textContent = 'RUNNING';
      successAlert.style.display = 'none';

      terminalOutput.textContent = `🚀 [Start] Initializing code generation for project: ${selectedProject.name}\n` +
        `📝 Prompt: ${prompt}\n\n`;

      try {
        const response = await fetch('/run', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            prompt: prompt,
            project: selectedProject.name,
          }),
        });

        if (!response.ok) {
          throw new Error(`Server returned HTTP ${response.status}: ${await response.text()}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          terminalOutput.textContent += chunk;
          terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }

        streamStatus.className = 'terminal-badge badge-success';
        streamStatus.textContent = 'COMPLETED';

        // Show Success Alert
        alertTitle.textContent = `Successfully updated project '${selectedProject.name}'!`;
        alertSub.textContent = `Code pushed directly to ${selectedProject.name}/ in GitHub. Google Cloud Run deployment triggered.`;
        alertLink.href = `https://github.com/noam2030/remote-code-agent-output/tree/main/${selectedProject.name}`;
        successAlert.style.display = 'flex';

        // Reload project details to refresh files list
        await loadProjects(selectedProject.name);

      } catch (err) {
        console.error('Generation error:', err);
        terminalOutput.textContent += `\n❌ [Error] ${err.message}\n`;
        streamStatus.className = 'terminal-badge badge-idle';
        streamStatus.textContent = 'ERROR';
      } finally {
        isGenerating = false;
        btnGenerate.disabled = false;
        btnGenerate.innerHTML = '<span>✨ Generate & Push to GitHub</span>';
      }
    }

    btnGenerate.addEventListener('click', startGeneration);

    // Initial Load
    loadProjects();
  </script>
</body>
</html>
"""
