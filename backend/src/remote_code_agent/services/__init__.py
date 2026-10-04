"""Backend services package for Remote Code Agent."""

from remote_code_agent.services.code_creation import (
    BASE_WORKSPACE,
    format_stream_chunk,
    generate_code_stream,
    get_agent_config,
)
from remote_code_agent.services.github_service import (
    check_github_auth,
    derive_project_slug,
    get_github_env,
    publish_project_to_github,
)
from remote_code_agent.services.project_service import (
    count_file_lines,
    delete_project,
    get_project_details,
    get_project_file_content,
    inspect_project_files,
    list_projects,
    load_project_stats,
    record_project_run_tokens,
    sanitize_project_name,
    sync_project_from_github,
)
from remote_code_agent.services.prompt_service import (
    PROMPT_FILE_NAME,
    extract_baseline_from_readme,
    get_project_prompt_path,
    read_project_prompt,
    synthesize_master_prompt_with_ai,
    synthesize_prompts_fallback,
    update_project_master_prompt,
    write_project_prompt,
)

__all__ = [
    "BASE_WORKSPACE",
    "format_stream_chunk",
    "generate_code_stream",
    "get_agent_config",
    "check_github_auth",
    "derive_project_slug",
    "get_github_env",
    "publish_project_to_github",
    "list_projects",
    "get_project_details",
    "get_project_file_content",
    "delete_project",
    "sanitize_project_name",
    "sync_project_from_github",
    "count_file_lines",
    "inspect_project_files",
    "load_project_stats",
    "record_project_run_tokens",
    "PROMPT_FILE_NAME",
    "get_project_prompt_path",
    "read_project_prompt",
    "write_project_prompt",
    "extract_baseline_from_readme",
    "synthesize_prompts_fallback",
    "synthesize_master_prompt_with_ai",
    "update_project_master_prompt",
]
