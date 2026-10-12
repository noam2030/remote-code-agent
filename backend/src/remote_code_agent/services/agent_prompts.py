"""Service responsible for loading agent prompts and dynamically fetching skills from GitHub."""

import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from remote_code_agent.core.config import DEFAULT_SKILLS_REPO_URL, SKILLS_REPO_URL

logger = logging.getLogger(__name__)

# Global in-memory cache for dynamically loaded skills
_LOADED_SKILLS: dict[str, str] = {}

FALLBACK_SKILLS: dict[str, str] = {
    "project-specification": """---
name: project-specification
description: Maintain a single, authoritative SPEC.md that captures the complete, current state of a project containing all mandatory sections 1 to 12 (Overview, Requirements, User Experience, Architecture, Technology Stack, Backend, Frontend, Data Model, API, Configuration, Testing, Deployment) so another coding agent can recreate the project from scratch without the original conversation. Defines what a project specification is and how to write it. Use when the user asks to create, update, or review SPEC.md, or when bootstrapping a new project from an existing SPEC.md.
---


### Required Content

Every created or updated `SPEC.md` must strictly contain **all sections 1 to 12**. No section from 1 to 12 may be omitted:

```markdown
# Project Specification

## 1. Overview
What the application does and its main goal.

## 2. Requirements
Complete functional requirements.

## 3. User Experience
UI, workflows, user interactions, and behavior.

## 4. Architecture
System architecture and major components.

## 5. Technology Stack
Languages, frameworks, libraries, databases, infrastructure, and tools.

## 6. Backend
Backend structure, services, APIs, business logic, and integrations.

## 7. Frontend
Pages, components, state management, styling, and client-side behavior.

## 8. Data Model
Entities, schemas, relationships, indexes, and persistence.

## 9. API
Endpoints, request/response formats, authentication, and errors.

## 10. Configuration
Environment variables, configuration files, secrets, and external dependencies.

## 11. Testing
Required tests and testing strategy.

## 12. Deployment
Build, deployment, infrastructure, and runtime requirements.
```
""",
    "development-workflow": """# development-workflow Skill

### 1. Code Modification Workflow
When the user explicitly requests code changes, new features, bug fixes, or requirement updates:

1. **Maintain Prompt History (`prompt.txt`)**:
   - For each project, maintain a `prompt.txt` file located in the project root directory.
   - Each user prompt must be appended to this file, separated by a new line.
   - For each prompt, prefix a sequential prompt number (e.g., `1. <user prompt>`, `2. <user prompt>`, etc., continuing the sequence if `prompt.txt` already exists).

2. **Code as a Reflection of the Spec File (`SPEC.md`)**:
   - The code must always be an exact reflection of the project specification file (`SPEC.md`).
   - Every implementation, modification, or bug fix must strictly conform to the architecture, data models, APIs, and requirements defined in `SPEC.md`.
   - Never write code or introduce architectural changes that deviate from or contradict `SPEC.md`.

3. **Requirement Updates (Spec First, Then Code)**:
   - Upon any new prompt that asks to update requirements, add new features, or alter system behavior:
     - **Update the spec first**: First update `SPEC.md` to reflect the new requirements, architecture, data models, or APIs.
     - **Then implement according to the spec**: Implement the code changes strictly according to the updated `SPEC.md`.
     - Never write or modify code before the specification is updated to reflect the new requirements.

4. **Pre-Implementation Confirmation Loop**:
   - Before any code change or file modification (excluding the recording of user prompts to `prompt.txt`), the agent must explain in short what it is about to do, summarize the planned changes (including any updates to `SPEC.md` and the codebase), and ask the explicit question: `Confirm?`
   - Pause/yield the turn (stop calling tools) and wait for the user's response.
   - Run this alignment loop until the user explicitly confirms (e.g., replies "yes" or "confirm").
   - If the user asks clarification questions or asks to implement the change differently:
     - Answer the questions thoroughly.
     - Adapt the plan according to the user's feedback.
     - Summarize the updated plan and ask `Confirm?` again.
     - Yield the turn and repeat until explicit confirmation is received.

5. **Strict Adherence to the Agreed Implementation**:
   - Once the user confirms, implement the changes strictly as agreed: update `SPEC.md` first, then implement the code according to the updated specification.
   - If an obstacle, error, or limitation arises during implementation that prevents implementing the plan as agreed:
     - Stop immediately and report the exact issue, explain why the agreed approach cannot proceed as planned, and suggest potential alternatives for the user to review.

6. **Side Branches & Pull Requests**:
   - Create a dedicated side branch for each feature, refactor, or bug fix.
   - Commit and push changes to GitHub on the side branch and open a pull request.

7. **Automated Testing**:
   - Ensure automated tests run on pull requests (e.g., via a GitHub Actions CI workflow).
   - Pull requests must only be allowed to merge if all automated tests pass.

8. **Pull Request Review & Merge Approval**:
   - Do NOT merge the pull request without explicit user approval.
   - Present the pull request URL to the user.
   - The user will review the pull request and give explicit confirmation before the pull request can be merged.

9. **Continuous Deployment Setup**:
   - For each project:
     - Maintain a GitHub Actions workflow that automatically deploys to production on Google Cloud when code is merged into `main`.
""",
}


def parse_github_tree_url(url: str) -> dict[str, str]:
    """Parses a GitHub repository tree URL into owner, repo, branch, and relative path.

    Example:
    'https://github.com/noam2030/build-with-agent/tree/main/.agents/skills'
    returns:
    {'owner': 'noam2030', 'repo': 'build-with-agent', 'branch': 'main', 'path': '.agents/skills'}
    """
    cleaned = url.strip().rstrip("/")
    pattern = r"^https?://github\.com/([^/]+)/([^/]+)(?:/(?:tree|blob)/([^/]+)/(.*))?$"
    match = re.match(pattern, cleaned)
    if not match:
        raise ValueError(f"Invalid GitHub repository URL: {url}")
    owner, repo, branch, path = match.groups()
    return {
        "owner": owner,
        "repo": repo,
        "branch": branch or "main",
        "path": (path or "").strip("/"),
    }


def _fetch_url_text(url: str | None, token: str | None = None, timeout: float = 10.0) -> str | None:
    """Helper to fetch raw text from an HTTP/HTTPS URL with optional bearer authentication."""
    if not url:
        return None
    headers = {"User-Agent": "remote-code-agent"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        logger.debug(f"Failed to fetch url text from {url}: {e}")
        return None


def fetch_remote_skills(repo_url: str | None = None) -> dict[str, str]:
    """Fetches skills dynamically from the remote GitHub repository.

    Queries the GitHub Contents API to discover skill directories, and downloads
    the corresponding SKILL.md files. Falls back to direct raw downloads if API is restricted.
    """
    target_url = repo_url or os.environ.get("SKILLS_REPO_URL") or SKILLS_REPO_URL or DEFAULT_SKILLS_REPO_URL
    parsed = parse_github_tree_url(target_url)
    owner = parsed["owner"]
    repo = parsed["repo"]
    branch = parsed["branch"]
    path = parsed["path"]

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "User-Agent": "remote-code-agent",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    discovered_skills: dict[str, str] = {}

    # 1. Query GitHub Contents API to list entries in the skills path
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if isinstance(data, list):
            for item in data:
                item_name = item.get("name")
                item_type = item.get("type")
                if item_type == "dir" and item_name:
                    # Conventional skill directory containing SKILL.md
                    raw_skill_url = (
                        f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"
                        f"{path}/{item_name}/SKILL.md"
                    )
                    content = _fetch_url_text(raw_skill_url, token=token)
                    if content:
                        discovered_skills[item_name] = content
                elif item_type == "file" and item_name and item_name.endswith(".md"):
                    content = _fetch_url_text(item.get("download_url"), token=token)
                    if content:
                        skill_key = item_name[:-3]
                        discovered_skills[skill_key] = content
    except Exception as e:
        logger.debug(f"GitHub Contents API listing failed for {api_url}: {e}")

    # 2. Fallback direct raw fetch for standard known skills if API listing was unavailable or rate-limited
    if not discovered_skills:
        for default_skill in ["development-workflow", "project-specification"]:
            raw_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"
                f"{path}/{default_skill}/SKILL.md"
            )
            content = _fetch_url_text(raw_url, token=token)
            if content:
                discovered_skills[default_skill] = content

    return discovered_skills


def load_dynamic_skills(
    repo_url: str | None = None,
    force_refresh: bool = False,
) -> dict[str, str]:
    """Loads skills dynamically from the remote GitHub repository into the in-memory cache.

    If network is unavailable or remote query returns empty, gracefully applies
    the offline fallback skills cache to guarantee continuous operation.
    """
    global _LOADED_SKILLS
    if _LOADED_SKILLS and not force_refresh:
        return dict(_LOADED_SKILLS)

    try:
        remote_skills = fetch_remote_skills(repo_url=repo_url)
    except Exception as e:
        logger.warning(f"Error fetching remote skills from {repo_url}: {e}")
        remote_skills = {}

    if not remote_skills:
        # Fall back to built-in cache
        remote_skills = dict(FALLBACK_SKILLS)

    _LOADED_SKILLS = remote_skills
    return dict(_LOADED_SKILLS)


def get_loaded_skills() -> dict[str, str]:
    """Returns currently loaded skills dictionary, loading dynamically if not loaded yet."""
    global _LOADED_SKILLS
    if not _LOADED_SKILLS:
        load_dynamic_skills()
    return dict(_LOADED_SKILLS)


def set_loaded_skills(skills: dict[str, str]) -> None:
    """Directly sets loaded skills in memory (useful for testing and mocking)."""
    global _LOADED_SKILLS
    _LOADED_SKILLS = dict(skills)


def clear_loaded_skills() -> None:
    """Clears the in-memory skills cache."""
    global _LOADED_SKILLS
    _LOADED_SKILLS = {}


def load_skill(skill_name: str) -> str:
    """Returns the text for a specific skill from the dynamically loaded skills."""
    skills = get_loaded_skills()
    if skill_name in skills:
        return skills[skill_name]
    raise FileNotFoundError(f"Missing dynamic skill document: {skill_name}")


def get_combined_skills() -> str:
    """Combines all dynamically loaded skills into a formatted string for prompt injection."""
    skills = get_loaded_skills()
    ordered_keys: list[str] = []
    for core in ["project-specification", "development-workflow"]:
        if core in skills:
            ordered_keys.append(core)
    for k in sorted(skills.keys()):
        if k not in ordered_keys:
            ordered_keys.append(k)
    return "\n\n".join(skills[k] for k in ordered_keys)


def find_docs_dir() -> Path:
    """Discovers the docs directory across local backend workspaces and container environments."""
    if "AGENT_DOCS_DIR" in os.environ:
        custom_path = Path(os.environ["AGENT_DOCS_DIR"]).resolve()
        if custom_path.is_dir():
            return custom_path

    current_file = Path(__file__).resolve()
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


def _extract_section(markdown_text: str, section_number: int) -> str:
    """Extracts a numbered top-level section (e.g. '## 1. ...') from markdown text."""
    pattern = rf"##\s*{section_number}\.[^\n]*\n([\s\S]*?)(?=\n##\s*\d+\.|\Z)"
    match = re.search(pattern, markdown_text)
    if not match:
        raise ValueError(f"Could not find section {section_number} in prompt markdown")
    return match.group(1).strip()


def get_agent_system_prompt(target_name: str) -> str:
    """Constructs the code generation system instructions dynamically."""
    raw_md = load_prompt_markdown()
    section_template = _extract_section(raw_md, 1)

    combined_skills = get_combined_skills()

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
    """Constructs the code generation chat prompt message dynamically."""
    raw_md = load_prompt_markdown()
    section_template = _extract_section(raw_md, 4)

    combined_skills = get_combined_skills()

    prompt = section_template.replace("{skills}", combined_skills)
    prompt = prompt.replace("{app_name}", app_name)
    prompt = prompt.replace("{user_instruction}", user_instruction)
    return prompt


def get_planning_chat_prompt(app_name: str, user_instruction: str, branch_name: str) -> str:
    """Constructs the planning chat prompt message dynamically from backend/docs/."""
    raw_md = load_prompt_markdown()
    section_template = _extract_section(raw_md, 5)

    prompt = section_template.replace("{app_name}", app_name)
    prompt = prompt.replace("{user_instruction}", user_instruction)
    prompt = prompt.replace("{branch_name}", branch_name)
    return prompt
