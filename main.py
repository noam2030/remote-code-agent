"""Entrypoint for the Google Antigravity Agent Service."""

import os
import sys

# Ensure src/ is on sys.path if running directly from repository root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from remote_code_agent.main import main
from remote_code_agent.server import app

if __name__ == "__main__":
    main()
