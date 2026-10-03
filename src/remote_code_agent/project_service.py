"""Service for discovering, managing, and syncing projects across GitHub and local workspace."""

import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

from remote_code_agent.config import GITHUB_OUTPUT_REPO, load_env_file
from remote_code_agent.github_service import (
    get_github_env,
    resolve_output_repo_full_name,
)

load_env_file()

BASE_WORKSPACE = os.path.abspath(os.environ.get("AGENT_WORKSPACE", "workspace"))
os.makedirs(BASE_WORKSPACE, exist_ok=True)


def sanitize_project_name(name: str) -> str:
    """Sanitizes project name to a clean lowercase kebab-case slug."""
    if not name:
        return "agent-app"
    s = name.strip().lower()
    s = s.replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"\-+", "-", s).strip("-")
    return s if s else "agent-app"


def parse_readme_projects(readme_content: str) -> dict[str, dict[str, str]]:
    """Extracts project entries and Cloud Run URLs from repository root README.md content.

    Matches patterns like:
    - [hello-world-from-2052](https://...run.app) (Live Cloud Run App) | [Source Code](./hello-world-from-2052/)
    or:
    - [hello-world-from-2052](./hello-world-from-2052/): description
    """
    projects: dict[str, dict[str, str]] = {}
    if not readme_content:
        return projects

    # Regex for live app url: - [project_name](url) (Live Cloud Run App)
    pattern_with_url = re.compile(
        r"-\s*\[([a-zA-Z0-9_\-]+)\]\((https?://[^)]+)\)\s*(?:\([^)]*\))?(?:\s*\|\s*\[Source Code\]\([^)]+\))?",
        re.MULTILINE,
    )
    for match in pattern_with_url.finditer(readme_content):
        name = match.group(1)
        url = match.group(2)
        projects[name] = {"cloud_run_url": url}

    # Regex for standard bullet entries: - [project_name](...)
    pattern_bullets = re.compile(
        r"-\s*\[([a-zA-Z0-9_\-]+)\](?:\(([^)]*)\))?(?::\s*([^\n]+))?",
        re.MULTILINE,
    )
    for match in pattern_bullets.finditer(readme_content):
        name = match.group(1)
        link = match.group(2) or ""
        desc = match.group(3) or ""
        if name not in projects:
            projects[name] = {}
        if link.startswith("http") and "cloud_run_url" not in projects[name]:
            projects[name]["cloud_run_url"] = link
        if desc:
            projects[name]["description"] = desc.strip()

    return projects


def list_remote_projects(
    target_repo: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Discovers project directories and live URLs from the central GitHub output repository."""
    if env is None:
        env = get_github_env()

    full_repo = resolve_output_repo_full_name(target_repo, env=env)
    projects: dict[str, dict[str, Any]] = {}

    # Attempt to fetch README.md to parse live URLs
    readme_content = ""
    try:
        readme_res = subprocess.run(
            ["gh", "api", f"repos/{full_repo}/readme", "-q", ".content"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if readme_res.returncode == 0 and readme_res.stdout.strip():
            import base64

            readme_content = base64.b64decode(readme_res.stdout.strip()).decode("utf-8", errors="ignore")
    except Exception:
        pass

    readme_metadata = parse_readme_projects(readme_content)

    # Attempt to fetch directory listing via gh api
    try:
        contents_res = subprocess.run(
            ["gh", "api", f"repos/{full_repo}/contents", "-q", ".[] | {name: .name, type: .type}"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if contents_res.returncode == 0 and contents_res.stdout.strip():
            import json

            for line in contents_res.stdout.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    name = item.get("name")
                    item_type = item.get("type")
                    if (
                        item_type == "dir"
                        and name
                        and not name.startswith(".")
                        and name not in {"scripts", "tests"}
                    ):
                        projects[name] = {
                            "name": name,
                            "github_url": f"https://github.com/{full_repo}/tree/main/{name}",
                            "cloud_run_url": readme_metadata.get(name, {}).get("cloud_run_url"),
                            "has_remote": True,
                        }
                except Exception:
                    continue
    except Exception:
        pass

    # If gh api was unavailable or returned nothing, populate from readme_metadata
    for name, meta in readme_metadata.items():
        if name not in projects and not name.startswith(".") and name not in {"scripts", "tests"}:
            projects[name] = {
                "name": name,
                "github_url": f"https://github.com/{full_repo}/tree/main/{name}",
                "cloud_run_url": meta.get("cloud_run_url"),
                "has_remote": True,
            }

    return projects


def list_local_projects(workspace_dir: str = BASE_WORKSPACE) -> dict[str, dict[str, Any]]:
    """Discovers project directories inside the local workspace."""
    projects: dict[str, dict[str, Any]] = {}
    if not os.path.exists(workspace_dir):
        return projects

    for entry in sorted(os.listdir(workspace_dir)):
        p_dir = os.path.join(workspace_dir, entry)
        if os.path.isdir(p_dir) and not entry.startswith("."):
            files = []
            for root, _, filenames in os.walk(p_dir):
                if ".git" in root:
                    continue
                rel_root = os.path.relpath(root, p_dir)
                for f in filenames:
                    if f.startswith("."):
                        continue
                    rel_path = f if rel_root == "." else os.path.join(rel_root, f)
                    files.append(rel_path)

            projects[entry] = {
                "name": entry,
                "is_local": True,
                "local_path": p_dir,
                "files": sorted(files),
                "files_count": len(files),
            }
    return projects


def list_projects() -> list[dict[str, Any]]:
    """Combines remote GitHub projects and local workspace projects into a unified project catalog."""
    full_repo = resolve_output_repo_full_name()
    remote_projects = list_remote_projects(target_repo=full_repo)
    local_projects = list_local_projects()

    merged: dict[str, dict[str, Any]] = {}

    # Add all remote projects
    for name, data in remote_projects.items():
        merged[name] = {
            "name": name,
            "github_url": data.get("github_url", f"https://github.com/{full_repo}/tree/main/{name}"),
            "cloud_run_url": data.get("cloud_run_url"),
            "has_remote": True,
            "is_local": False,
            "files": [],
            "files_count": 0,
        }

    # Overlay local projects
    for name, data in local_projects.items():
        if name in merged:
            merged[name]["is_local"] = True
            merged[name]["local_path"] = data.get("local_path")
            merged[name]["files"] = data.get("files", [])
            merged[name]["files_count"] = data.get("files_count", 0)
        else:
            merged[name] = {
                "name": name,
                "github_url": f"https://github.com/{full_repo}/tree/main/{name}",
                "cloud_run_url": None,
                "has_remote": False,
                "is_local": True,
                "local_path": data.get("local_path"),
                "files": data.get("files", []) ,
                "files_count": data.get("files_count", 0),
            }

    # Return list sorted alphabetically by name
    return sorted(list(merged.values()), key=lambda p: p["name"])


def sync_project_from_github(
    project_name: str,
    target_dir: str,
    target_repo: str | None = None,
) -> bool:
    """Syncs existing project files from the GitHub repository into target_dir.

    Returns True if project files were found and copied, False otherwise.
    """
    env = get_github_env()
    full_repo = resolve_output_repo_full_name(target_repo, env=env)

    with tempfile.TemporaryDirectory() as tmp_dir:
        res = subprocess.run(
            ["git", "clone", "--depth", "1", f"https://github.com/{full_repo}.git", tmp_dir],
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            return False

        src_proj = os.path.join(tmp_dir, project_name)
        if not os.path.isdir(src_proj):
            return False

        os.makedirs(target_dir, exist_ok=True)
        copied_any = False
        for item in os.listdir(src_proj):
            if item == ".git":
                continue
            src_item = os.path.join(src_proj, item)
            dst_item = os.path.join(target_dir, item)
            if os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                copied_any = True
            else:
                shutil.copy2(src_item, dst_item)
                copied_any = True

        return copied_any


def get_project_details(project_name: str) -> dict[str, Any] | None:
    """Returns detailed information, file tree, and README for a specific project.

    If the project exists in GitHub but not locally, syncs it to local workspace.
    """
    clean_name = sanitize_project_name(project_name)
    local_dir = os.path.join(BASE_WORKSPACE, clean_name)

    # If local directory does not exist or has no files, try syncing from GitHub
    has_local_files = os.path.isdir(local_dir) and any(
        not f.startswith(".") for f in os.listdir(local_dir)
    )
    if not has_local_files:
        sync_project_from_github(clean_name, local_dir)

    all_projects = {p["name"]: p for p in list_projects()}
    project_info = all_projects.get(clean_name) or {
        "name": clean_name,
        "github_url": f"https://github.com/{resolve_output_repo_full_name()}/tree/main/{clean_name}",
        "cloud_run_url": None,
        "has_remote": False,
        "is_local": os.path.isdir(local_dir),
    }

    # Inspect files in local directory
    files: list[str] = []
    readme_text = ""
    if os.path.isdir(local_dir):
        for root, _, filenames in os.walk(local_dir):
            if ".git" in root:
                continue
            rel_root = os.path.relpath(root, local_dir)
            for f in filenames:
                if f.startswith("."):
                    continue
                rel_path = f if rel_root == "." else os.path.join(rel_root, f)
                files.append(rel_path)

        readme_file = os.path.join(local_dir, "README.md")
        if os.path.exists(readme_file):
            try:
                with open(readme_file, "r", encoding="utf-8") as f:
                    readme_text = f.read()
            except Exception:
                pass

    project_info["files"] = sorted(files)
    project_info["files_count"] = len(files)
    project_info["readme"] = readme_text
    return project_info
