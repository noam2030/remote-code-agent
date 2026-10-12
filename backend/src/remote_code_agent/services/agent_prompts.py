"""Service responsible for loading agent prompts and skills dynamically from services/docs/."""

import os
import re
from pathlib import Path


def find_docs_dir() -> Path:
    """Discovers the docs directory across local backend workspaces and container environments."""
    if "AGENT_DOCS_DIR" in os.environ:
        custom_path = Path(os.environ["AGENT_DOCS_DIR"]).resolve()
        if custom_path.is_dir():
            return custom_path

    current_file = Path(__file__).resolve()
    # Co-located inside services/ package: current_file.parent / "docs"
    # Fallback to backend root /docs or container paths if needed
    candidates = [
        current_file.parent / "docs",
        current_file.parents[3] / "docs",
        Path.cwd() / "backend" / "src" / "remote_code_agent" / "services" / "docs",
        Path.cwd() / "backend" / "docs",
        Path.cwd() / "docs",
        Path("/app/src/remote_code_agent/services/docs"),
        Path("/app/docs"),
    ]
    for cand in candidates:
        if cand.is_dir() and (cand / "prompt.md").is_file():
            return cand

    for cand in candidates:
        if cand.is_dir():
            return cand

    return candidates[0]


def load_prompt_markdown() -> str:
    """Loads the raw content of prompt.md from disk."""
    docs_dir = find_docs_dir()
    prompt_file = docs_dir / "prompt.md"
    if not prompt_file.is_file():
        raise FileNotFoundError(f"Missing prompt document at: {prompt_file}")
    return prompt_file.read_text(encoding="utf-8")


def load_skill(skill_name: str) -> str:
    """Loads an individual skill markdown file from skills/<skill_name>.md."""
    docs_dir = find_docs_dir()
    skill_file = docs_dir / "skills" / f"{skill_name}.md"
    if not skill_file.is_file():
        raise FileNotFoundError(f"Missing skill document at: {skill_file}")
    return skill_file.read_text(encoding="utf-8")


def _extract_section(markdown_text: str, section_number: int) -> str:
    """Extracts a numbered top-level section (e.g. '## 1. ...') from markdown text."""
    pattern = rf"##\s*{section_number}\.[^\n]*\n([\s\S]*?)(?=\n##\s*\d+\.|\Z)"
    match = re.search(pattern, markdown_text)
    if not match:
        raise ValueError(f"Could not find section {section_number} in prompt markdown")
    return match.group(1).strip()


def get_agent_system_prompt(target_name: str) -> str:
    """Constructs the code generation system instructions dynamically from backend/docs/."""
    raw_md = load_prompt_markdown()
    section_template = _extract_section(raw_md, 1)

    spec_skill = load_skill("project-specification")
    dev_skill = load_skill("development-workflow")
    combined_skills = f"{spec_skill}\n\n{dev_skill}"

    prompt = section_template.replace("{skills}", combined_skills)
    prompt = prompt.replace("{target_name}", target_name)
    return prompt


def get_info_retrieval_system_prompt(target_name: str) -> str:
    """Constructs the info retrieval system instructions dynamically from backend/docs/."""
    raw_md = load_prompt_markdown()
    section_template = _extract_section(raw_md, 2)
    return section_template.replace("{target_name}", target_name)


def get_prompt_synthesis_system_prompt(app_name: str) -> str:
    """Constructs the master prompt synthesis system instructions dynamically from backend/docs/."""
    raw_md = load_prompt_markdown()
    section_template = _extract_section(raw_md, 3)
    return section_template.replace("{app_name}", app_name)


def get_user_chat_prompt(app_name: str, user_instruction: str) -> str:
    """Constructs the code generation chat prompt message dynamically from backend/docs/."""
    raw_md = load_prompt_markdown()
    section_template = _extract_section(raw_md, 4)

    spec_skill = load_skill("project-specification")
    dev_skill = load_skill("development-workflow")
    combined_skills = f"{spec_skill}\n\n{dev_skill}"

    prompt = section_template.replace("{skills}", combined_skills)
    prompt = prompt.replace("{app_name}", app_name)
    prompt = prompt.replace("{user_instruction}", user_instruction)
    return prompt
