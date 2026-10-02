"""Remote Code Agent - Autonomous code generation using Google Antigravity."""

from remote_code_agent.code_creation import (
    BASE_WORKSPACE,
    format_stream_chunk,
    generate_code_stream,
    get_agent_config,
)
from remote_code_agent.server import app

__version__ = "0.1.0"

__all__ = [
    "app",
    "BASE_WORKSPACE",
    "format_stream_chunk",
    "generate_code_stream",
    "get_agent_config",
    "__version__",
]
