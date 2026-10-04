"""Service for discovering, managing, and syncing projects across GitHub and local workspace."""

import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

from remote_code_agent.config import GITHUB_OUTPUT_REPO, load_env_file
from remote_code_agent.github_service import (
    check_github_auth,
    ensure_git_config,
    get_authenticated_repo_url,
    get_github_env,
    resolve_output_repo_full_name,
    sanitize_git_output,
)

load_env_file()

BASE_WORKSPACE = os.path.abspath(os.environ.get("AGENT_WORKSPACE", "workspace"))
os.makedirs(BASE_WORKSPACE, exist_ok=True)

# Common binary file extensions to avoid decoding as text
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svgz", ".webp",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".pdf", ".exe", ".bin", ".so", ".dylib", ".dll",
    ".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".sqlite3",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}


def sanitize_project_name(name: str) -> str:
    """Sanitizes project name to a clean lowercase kebab-case slug."""
    if not name:
        return "agent-app"
    s = name.strip().lower()
    s = s.replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"\-+", "-", s).strip("-")
    return s if s else "agent-app"


def is_binary_file(file_path: str) -> bool:
    """Checks whether a file is binary by extension or content."""
    _, ext = os.path.splitext(file_path)
    if ext.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
    except Exception:
        pass
    return False


def count_file_lines(file_path: str) -> int:
    """Counts lines in a text file. Returns 0 for binary or unreadable files."""
    if is_binary_file(file_path):
        return 0
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def inspect_project_files(project_dir: str) -> tuple[list[dict[str, Any]], int]:
    """Inspects all files in a project workspace.

    Returns:
        (files_detail, total_lines_of_code)
    """
    files_detail: list[dict[str, Any]] = []
    total_loc = 0

    if not os.path.isdir(project_dir):
        return files_detail, total_loc

    for root, dirs, filenames in os.walk(project_dir):
        # Exclude hidden directories and caches
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"__pycache__", "node_modules"}]
        for fname in sorted(filenames):
            if fname.startswith("."):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, project_dir)
            _, ext = os.path.splitext(fname)

            is_bin = is_binary_file(full_path)
            lines = 0 if is_bin else count_file_lines(full_path)
            size = 0
            try:
                size = os.path.getsize(full_path)
            except Exception:
                pass

            total_loc += lines
            files_detail.append({
                "path": rel_path,
                "name": fname,
                "lines": lines,
                "size_bytes": size,
                "extension": ext.lower(),
                "is_binary": is_bin,
            })

    files_detail.sort(key=lambda x: x["path"])
    return files_detail, total_loc


def get_project_stats_file(project_name: str, workspace_dir: str = BASE_WORKSPACE) -> str:
    """Returns the path to the project's stats JSON file."""
    clean_name = sanitize_project_name(project_name)
    return os.path.join(workspace_dir, clean_name, ".agent_stats.json")


def load_project_stats(project_name: str, workspace_dir: str = BASE_WORKSPACE) -> dict[str, Any]:
    """Loads cumulative token and build statistics for a project."""
    stats_file = get_project_stats_file(project_name, workspace_dir=workspace_dir)
    if os.path.exists(stats_file):
        try:
            import json
            with open(stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {
                        "total_tokens": int(data.get("total_tokens", 0)),
                        "prompt_tokens": int(data.get("prompt_tokens", 0)),
                        "completion_tokens": int(data.get("completion_tokens", 0)),
                        "build_runs": int(data.get("build_runs", 0)),
                        "last_run_tokens": int(data.get("last_run_tokens", 0)),
                        "last_updated": data.get("last_updated"),
                        "is_estimated": bool(data.get("is_estimated", False)),
                    }
        except Exception:
            pass

    # If no stats file exists yet, estimate baseline from project LOC/files if available
    clean_name = sanitize_project_name(project_name)
    proj_dir = os.path.join(workspace_dir, clean_name)
    if os.path.isdir(proj_dir):
        _, loc = inspect_project_files(proj_dir)
        if loc > 0:
            # Baseline estimation: ~18 tokens per LOC for prompt context + code generation
            est_tokens = max(loc * 18, 500)
            return {
                "total_tokens": est_tokens,
                "prompt_tokens": int(est_tokens * 0.6),
                "completion_tokens": int(est_tokens * 0.4),
                "build_runs": 1,
                "last_run_tokens": est_tokens,
                "last_updated": None,
                "is_estimated": True,
            }

    return {
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "build_runs": 0,
        "last_run_tokens": 0,
        "last_updated": None,
        "is_estimated": False,
    }


def record_project_run_tokens(
    project_name: str,
    tokens: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    workspace_dir: str = BASE_WORKSPACE,
) -> dict[str, Any]:
    """Records and accumulates token usage for a project generation run."""
    import datetime
    import json

    clean_name = sanitize_project_name(project_name)
    proj_dir = os.path.join(workspace_dir, clean_name)
    os.makedirs(proj_dir, exist_ok=True)
    stats_file = get_project_stats_file(project_name, workspace_dir=workspace_dir)

    current_stats = load_project_stats(project_name, workspace_dir=workspace_dir)
    if current_stats.get("is_estimated"):
        # Replace estimated stats with actual recorded stats
        new_total = tokens
        new_prompt = prompt_tokens
        new_comp = completion_tokens
        new_runs = 1
    else:
        new_total = current_stats.get("total_tokens", 0) + tokens
        new_prompt = current_stats.get("prompt_tokens", 0) + prompt_tokens
        new_comp = current_stats.get("completion_tokens", 0) + completion_tokens
        new_runs = current_stats.get("build_runs", 0) + 1

    updated = {
        "total_tokens": new_total,
        "prompt_tokens": new_prompt,
        "completion_tokens": new_comp,
        "build_runs": new_runs,
        "last_run_tokens": tokens,
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "is_estimated": False,
    }

    try:
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2)
    except Exception:
        pass

    return updated


def get_project_file_content(
    project_name: str,
    file_path: str,
    workspace_dir: str = BASE_WORKSPACE,
) -> dict[str, Any]:
    """Safely retrieves the content and metadata of a project file.

    Guards against directory traversal attacks.
    """
    clean_name = sanitize_project_name(project_name)
    proj_dir = os.path.realpath(os.path.join(workspace_dir, clean_name))

    # If project workspace is missing files, attempt to sync from GitHub first
    if not os.path.isdir(proj_dir) or not os.listdir(proj_dir):
        sync_project_from_github(clean_name, proj_dir)

    if not os.path.isdir(proj_dir):
        raise FileNotFoundError(f"Project '{clean_name}' does not exist.")

    # Guard against directory traversal
    norm_path = os.path.normpath(file_path.strip().lstrip("/"))
    target_path = os.path.realpath(os.path.join(proj_dir, norm_path))

    if not (target_path == proj_dir or target_path.startswith(proj_dir + os.sep)):
        raise PermissionError("Access denied: invalid file path.")

    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"File '{file_path}' not found in project '{clean_name}'.")

    size_bytes = os.path.getsize(target_path)
    is_bin = is_binary_file(target_path)
    _, ext = os.path.splitext(target_path)

    if is_bin:
        return {
            "project": clean_name,
            "path": norm_path,
            "name": os.path.basename(target_path),
            "content": None,
            "lines": 0,
            "size_bytes": size_bytes,
            "is_binary": True,
            "extension": ext.lower(),
        }

    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            lines = len(content.splitlines())
    except Exception as e:
        raise OSError(f"Failed to read file: {e}")

    return {
        "project": clean_name,
        "path": norm_path,
        "name": os.path.basename(target_path),
        "content": content,
        "lines": lines,
        "size_bytes": size_bytes,
        "is_binary": False,
        "extension": ext.lower(),
    }


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
    """Discovers project directories inside the local workspace with file details, LOC, and token stats."""
    projects: dict[str, dict[str, Any]] = {}
    if not os.path.exists(workspace_dir):
        return projects

    for entry in sorted(os.listdir(workspace_dir)):
        p_dir = os.path.join(workspace_dir, entry)
        if os.path.isdir(p_dir) and not entry.startswith("."):
            files_detail, total_loc = inspect_project_files(p_dir)
            stats = load_project_stats(entry, workspace_dir=workspace_dir)
            files = [f["path"] for f in files_detail]

            projects[entry] = {
                "name": entry,
                "is_local": True,
                "local_path": p_dir,
                "files": files,
                "files_count": len(files),
                "files_detail": files_detail,
                "lines_of_code": total_loc,
                "tokens_spent": stats.get("total_tokens", 0),
                "stats": stats,
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
            "files_detail": [],
            "lines_of_code": 0,
            "tokens_spent": 0,
            "stats": {},
        }

    # Overlay local projects
    for name, data in local_projects.items():
        if name in merged:
            merged[name]["is_local"] = True
            merged[name]["local_path"] = data.get("local_path")
            merged[name]["files"] = data.get("files", [])
            merged[name]["files_count"] = data.get("files_count", 0)
            merged[name]["files_detail"] = data.get("files_detail", [])
            merged[name]["lines_of_code"] = data.get("lines_of_code", 0)
            merged[name]["tokens_spent"] = data.get("tokens_spent", 0)
            merged[name]["stats"] = data.get("stats", {})
        else:
            merged[name] = {
                "name": name,
                "github_url": f"https://github.com/{full_repo}/tree/main/{name}",
                "cloud_run_url": None,
                "has_remote": False,
                "is_local": True,
                "local_path": data.get("local_path"),
                "files": data.get("files", []),
                "files_count": data.get("files_count", 0),
                "files_detail": data.get("files_detail", []),
                "lines_of_code": data.get("lines_of_code", 0),
                "tokens_spent": data.get("tokens_spent", 0),
                "stats": data.get("stats", {}),
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
    repo_url = get_authenticated_repo_url(full_repo, env=env)

    with tempfile.TemporaryDirectory() as tmp_dir:
        res = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, tmp_dir],
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
    """Returns detailed information, file tree, LOC, token stats, and README for a specific project.

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

    # Inspect files and stats in local directory
    files_detail, total_loc = inspect_project_files(local_dir)
    stats = load_project_stats(clean_name, workspace_dir=BASE_WORKSPACE)
    files = [f["path"] for f in files_detail]

    readme_text = ""
    readme_file = os.path.join(local_dir, "README.md")
    if os.path.exists(readme_file):
        try:
            with open(readme_file, "r", encoding="utf-8") as f:
                readme_text = f.read()
        except Exception:
            pass

    project_info["files"] = files
    project_info["files_count"] = len(files)
    project_info["files_detail"] = files_detail
    project_info["lines_of_code"] = total_loc
    project_info["tokens_spent"] = stats.get("total_tokens", 0)
    project_info["stats"] = stats
    project_info["readme"] = readme_text
    return project_info


def delete_project(
    project_name: str,
    delete_remote: bool = True,
    target_repo: str | None = None,
) -> tuple[bool, str]:
    """Deletes a project locally and optionally from the central GitHub repository.

    1. Removes local project directory from BASE_WORKSPACE if it exists.
    2. If delete_remote=True:
       - Clones the central repository to a temp directory.
       - Removes the project directory with git rm -rf.
       - Strips references to project_name from root README.md.
       - Commits and pushes the deletion directly to main.
    Returns (success, message).
    """
    clean_name = sanitize_project_name(project_name)
    local_dir = os.path.join(BASE_WORKSPACE, clean_name)

    local_existed = os.path.exists(local_dir)
    if local_existed:
        shutil.rmtree(local_dir, ignore_errors=True)

    if not delete_remote:
        return True, f"Project '{clean_name}' deleted from local workspace."

    env = get_github_env()
    is_authed, auth_msg = check_github_auth(env)
    if not is_authed:
        if local_existed:
            return True, f"Project '{clean_name}' deleted locally, but GitHub authentication failed: {auth_msg}"
        return False, f"GitHub authentication required to delete remote project: {auth_msg}"

    ensure_git_config(env)
    full_repo = resolve_output_repo_full_name(target_repo, env=env)
    repo_url = get_authenticated_repo_url(full_repo, env=env)

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = os.path.join(tmp_dir, "output-repo")
        clone_res = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, repo_dir],
            env=env,
            capture_output=True,
            text=True,
        )
        if clone_res.returncode != 0:
            err_msg = sanitize_git_output(clone_res.stderr).strip()
            if local_existed:
                return True, f"Project '{clean_name}' deleted locally, but could not connect to GitHub: {err_msg}"
            return False, f"Failed to connect to GitHub repository: {err_msg}"

        proj_path = os.path.join(repo_dir, clean_name)
        remote_existed = os.path.isdir(proj_path)

        # Update root README.md to remove project line
        root_readme = os.path.join(repo_dir, "README.md")
        readme_changed = False
        if os.path.exists(root_readme):
            with open(root_readme, "r", encoding="utf-8") as f:
                content = f.read()

            new_lines = []
            for line in content.splitlines():
                if f"[{clean_name}]" in line or f"./{clean_name}/" in line:
                    readme_changed = True
                    continue
                new_lines.append(line)

            if readme_changed:
                with open(root_readme, "w", encoding="utf-8") as f:
                    f.write("\n".join(new_lines) + "\n")

        if not remote_existed and not readme_changed:
            if local_existed:
                return True, f"Project '{clean_name}' deleted from local workspace (was not present on GitHub)."
            return True, f"Project '{clean_name}' does not exist locally or on GitHub."

        if remote_existed:
            subprocess.run(["git", "rm", "-rf", clean_name], cwd=repo_dir, env=env, check=False)

        if readme_changed:
            subprocess.run(["git", "add", "README.md"], cwd=repo_dir, env=env, check=False)

        # Configure git user
        subprocess.run(["git", "config", "user.name", "Remote Code Agent"], cwd=repo_dir, env=env, check=True)
        subprocess.run(["git", "config", "user.email", "agent@remote-code-agent.local"], cwd=repo_dir, env=env, check=True)

        commit_res = subprocess.run(
            ["git", "commit", "-m", f"chore(delete): remove project {clean_name}"],
            cwd=repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        push_res = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        if push_res.returncode != 0:
            err_msg = sanitize_git_output(push_res.stderr).strip()
            return False, f"Failed to push deletion to GitHub: {err_msg}"

        return True, f"Project '{clean_name}' successfully deleted locally and from GitHub ({full_repo})."

