"""Remote Code Agent - Autonomous code generation using Google Antigravity."""

from remote_code_agent.config import (
    AGENT_WORKSPACE,
    GEMINI_API_KEY,
    GH_TOKEN,
    GITHUB_OUTPUT_REPO,
    PORT,
    load_env_file,
)
from remote_code_agent.code_creation import (
    BASE_WORKSPACE,
    format_stream_chunk,
    generate_code_stream,
    get_agent_config,
)
from remote_code_agent.project_service import (
    delete_project,
    get_project_details,
    list_projects,
    sanitize_project_name,
    sync_project_from_github,
)
from remote_code_agent.prompt_service import (
    get_project_prompt_path,
    read_project_prompt,
    update_project_master_prompt,
    write_project_prompt,
)
from remote_code_agent.web_ui import get_web_ui_html
from remote_code_agent.server import app

__version__ = "0.2.0"

__all__ = [
    "app",
    "BASE_WORKSPACE",
    "AGENT_WORKSPACE",
    "GEMINI_API_KEY",
    "GH_TOKEN",
    "GITHUB_OUTPUT_REPO",
    "PORT",
    "load_env_file",
    "format_stream_chunk",
    "generate_code_stream",
    "get_agent_config",
    "list_projects",
    "get_project_details",
    "delete_project",
    "sanitize_project_name",
    "sync_project_from_github",
    "get_project_prompt_path",
    "read_project_prompt",
    "write_project_prompt",
    "update_project_master_prompt",
    "get_web_ui_html",
    "__version__",
]
