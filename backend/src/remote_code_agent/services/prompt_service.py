"""Service for managing consolidated master prompt specifications (prompt.txt).

Maintains a canonical, self-contained prompt.txt for each project such that if
the master prompt is used on a brand new project, the agent will reproduce the
exact same unified application with all features and refinements.
"""

import os
import re
from typing import Optional

PROMPT_FILE_NAME = "prompt.txt"


def get_project_prompt_path(project_dir: str) -> str:
    """Returns the absolute path to prompt.txt in the project directory."""
    return os.path.join(project_dir, PROMPT_FILE_NAME)


def read_project_prompt(project_dir: str) -> Optional[str]:
    """Reads existing prompt.txt from project directory if available."""
    prompt_file = get_project_prompt_path(project_dir)
    if os.path.isfile(prompt_file):
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    return None


def write_project_prompt(project_dir: str, content: str) -> None:
    """Writes the updated master prompt to prompt.txt."""
    os.makedirs(project_dir, exist_ok=True)
    prompt_file = get_project_prompt_path(project_dir)
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


def extract_baseline_from_readme(project_dir: str) -> Optional[str]:
    """Extracts high-level features and description from README.md if prompt.txt does not exist."""
    readme_path = os.path.join(project_dir, "README.md")
    if not os.path.isfile(readme_path):
        return None
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract title and overview
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return None

        # Gather first header and bullet points or first paragraph
        extracted_parts = []
        for line in lines[:25]:
            if line.startswith("# ") or line.startswith("## ") or line.startswith("- ") or line.startswith("* "):
                extracted_parts.append(line)
            elif not line.startswith("```") and not line.startswith("[!") and len(extracted_parts) < 15:
                extracted_parts.append(line)

        if extracted_parts:
            return "\n".join(extracted_parts)
    except Exception:
        pass
    return None


def synthesize_prompts_fallback(
    existing_prompt: Optional[str],
    new_prompt: str,
    app_name: str,
) -> str:
    """Deterministic fallback synthesizer to merge prompts into a cohesive master prompt."""
    clean_new = new_prompt.strip()

    if not existing_prompt or not existing_prompt.strip():
        return (
            f"# Master Project Specification: {app_name}\n\n"
            "## Overview & Goal\n"
            f"Build a complete, production-ready application '{app_name}' satisfying the following specifications:\n\n"
            "## Core Requirements & Features\n"
            f"- {clean_new}\n\n"
            "## Technical Guidelines\n"
            "- Implement an interactive web interface or HTTP API with clean architecture.\n"
            "- Ensure deployment compatibility with Google Cloud Run (listen on 0.0.0.0:$PORT, default 8080).\n"
            f"- Any persistent data for the app must be stored in Google Cloud Firestore (project 'ai-learning-499409') as a dedicated collection named '{app_name}'.\n"
            "- If deployment is requested, generate GitHub Actions workflows targeting Google Cloud project 'ai-learning-499409' or Vercel 'noam-projects2'.\n"
            "- Provide automated tests in tests/ and a comprehensive README.md.\n"
        )

    # Check if the requirement is already fully contained
    if clean_new in existing_prompt:
        return existing_prompt

    # If existing prompt has a Core Requirements section, integrate into it
    core_req_match = re.search(r"(##\s*Core Requirements & Features[^\n]*\n)(.*?)(\n##|\Z)", existing_prompt, re.DOTALL)
    if core_req_match:
        section_header = core_req_match.group(1)
        section_body = core_req_match.group(2).rstrip()
        rest = core_req_match.group(3)

        updated_body = f"{section_body}\n- {clean_new}"
        return existing_prompt[:core_req_match.start()] + section_header + updated_body + rest + existing_prompt[core_req_match.end():]

    # Otherwise append as an additional features section
    return (
        f"{existing_prompt.strip()}\n\n"
        "## Additional Features & Refinements\n"
        f"- {clean_new}\n"
    )


async def synthesize_master_prompt_with_ai(
    existing_prompt: Optional[str],
    new_prompt: str,
    app_name: str,
) -> str:
    """Uses Google Antigravity Agent to synthesize prompts into a unified master specification."""
    try:
        import google.antigravity
        from google.antigravity import Agent, LocalAgentConfig

        system_instruction = (
            f"You are a Principal Software Architect and Master Prompt Engineer for the project '{app_name}'. "
            "Your task is to take the existing project master prompt specification and a newly provided incremental user prompt, "
            "and re-summarize/synthesize them into a SINGLE, unified master prompt specification. "
            "Requirements:\n"
            "1. The output must be written in such a way that if a developer or AI coding agent takes ONLY this synthesized prompt "
            "and uses it on a brand new, empty project, they will produce the exact same final application with all features, architecture, "
            "endpoints, styling, and refinements included.\n"
            "2. Ensure any requirement for persistent application data is captured as requiring storage in Google Cloud Firestore "
            f"(project 'ai-learning-499409') under a dedicated collection named '{app_name}'.\n"
            "3. If deployment is requested, capture requirements to add GitHub Actions deployment workflows for Google Cloud project 'ai-learning-499409' or Vercel 'noam-projects2'.\n"
            "4. Seamlessly merge all requirements. If the new prompt modifies, refines, or supersedes an earlier instruction, "
            "update that requirement rather than repeating contradictory instructions.\n"
            "5. Do NOT output conversational greetings, preamble, or wrapping markdown code fences (```). "
            "Output only the clean, complete master prompt specification text."
        )

        user_content = (
            f"Project Name: {app_name}\n\n"
            f"--- EXISTING MASTER SPECIFICATION ---\n"
            f"{existing_prompt or 'None (initial project prompt)'}\n\n"
            f"--- NEW USER PROMPT / FEATURE REQUEST ---\n"
            f"{new_prompt.strip()}\n\n"
            "Please output the synthesized, unified master prompt specification for the entire project:"
        )

        config = LocalAgentConfig(
            system_instructions=system_instruction,
        )

        accumulated = []
        async with Agent(config) as agent:
            response = await agent.chat(user_content)
            async for chunk in response.chunks:
                if hasattr(chunk, "text") and chunk.text:
                    accumulated.append(chunk.text)

        result = "".join(accumulated).strip()
        # If output was wrapped in markdown code fence, unwrap
        if result.startswith("```") and result.endswith("```"):
            lines = result.splitlines()
            if len(lines) >= 2:
                result = "\n".join(lines[1:-1]).strip()

        if len(result) >= 30:
            return result
    except Exception:
        pass

    # Fallback to deterministic synthesis if AI call fails or is unavailable
    return synthesize_prompts_fallback(existing_prompt, new_prompt, app_name)


async def update_project_master_prompt(
    project_dir: str,
    app_name: str,
    new_prompt: str,
) -> str:
    """Updates and re-summarizes prompt.txt for a project with the new user prompt.

    1. Reads existing prompt.txt (or extracts baseline from README.md if missing).
    2. Synthesizes into a unified master prompt specification.
    3. Saves the consolidated prompt to prompt.txt in project_dir.
    Returns the updated master prompt content.
    """
    clean_new = new_prompt.strip()
    if not clean_new:
        existing = read_project_prompt(project_dir)
        return existing or ""

    existing = read_project_prompt(project_dir)
    if not existing:
        # Check if project already has files/README that can provide baseline context
        baseline = extract_baseline_from_readme(project_dir)
        if baseline:
            existing = (
                f"# Master Project Specification: {app_name}\n\n"
                f"## Baseline Context\n{baseline}\n"
            )

    updated_prompt = await synthesize_master_prompt_with_ai(existing, clean_new, app_name)
    write_project_prompt(project_dir, updated_prompt)
    return updated_prompt
