import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

from remote_code_agent.config import GITHUB_OUTPUT_REPO, load_env_file

# Ensure .env is loaded if present
load_env_file()


def derive_project_slug(prompt: str) -> str:
    """Derives a clean kebab-case project and repository slug from the user prompt."""
    m = re.search(r'(?:named?|called)\s+([a-zA-Z0-9_\-]+)', prompt, re.IGNORECASE)
    if m:
        name = m.group(1).lower().replace('_', '-')
        if name not in {'a', 'an', 'the', 'new', 'this', 'my'}:
            return f"{name}-{str(int(time.time()))[-4:]}"

    words = re.findall(r'[a-zA-Z0-9]+', prompt.lower())
    stop_words = {
        'a', 'an', 'the', 'in', 'on', 'at', 'for', 'to', 'of', 'and', 'is', 'it',
        'with', 'write', 'create', 'build', 'make', 'generate', 'please', 'app',
        'application', 'repo', 'repository', 'script', 'code'
    }
    keywords = [w for w in words if w not in stop_words]
    base = '-'.join(keywords[:3]) if keywords else 'agent-app'
    ts = str(int(time.time()))[-4:]
    return f"{base}-{ts}"


def get_github_env() -> dict[str, str]:
    """Prepares environment variables for git and gh CLI operations, injecting GH_TOKEN if configured."""
    env = os.environ.copy()
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    return env


def check_github_auth(env: dict[str, str] | None = None) -> tuple[bool, str]:
    """Validates that GitHub authentication is available via GH_TOKEN/GITHUB_TOKEN or gh CLI status."""
    if env is None:
        env = get_github_env()

    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        return True, "Authenticated via GH_TOKEN/GITHUB_TOKEN environment variable."

    res = subprocess.run(["gh", "auth", "status"], env=env, capture_output=True, text=True)
    if res.returncode == 0:
        return True, "Authenticated via GitHub CLI."

    return False, (
        "GitHub authentication missing: Neither GH_TOKEN nor GITHUB_TOKEN is set in environment or .env, "
        "and GitHub CLI is not authenticated. Please set GH_TOKEN with 'repo' scope."
    )


def ensure_git_config(env: dict[str, str] | None = None):
    """Ensures git has an author name, email, and credential helper configured for automated commits."""
    if env is None:
        env = get_github_env()
    try:
        subprocess.run(["git", "config", "user.name"], check=True, capture_output=True, env=env)
    except subprocess.CalledProcessError:
        subprocess.run(["git", "config", "--global", "user.name", "Remote Code Agent"], check=True, env=env)
        subprocess.run(["git", "config", "--global", "user.email", "agent@remote-code-agent.local"], check=True, env=env)

    # Setup gh credential helper for git commands
    subprocess.run(["gh", "auth", "setup-git"], check=False, capture_output=True, env=env)


def get_github_owner(env: dict[str, str] | None = None) -> str:
    """Returns the authenticated GitHub username or defaults to 'noam2030'."""
    if env is None:
        env = get_github_env()
    owner_res = subprocess.run(["gh", "api", "user", "-q", ".login"], env=env, capture_output=True, text=True)
    if owner_res.returncode == 0 and owner_res.stdout.strip():
        return owner_res.stdout.strip()
    return "noam2030"


def resolve_output_repo_full_name(target_repo: str | None = None, env: dict[str, str] | None = None) -> str:
    """Resolves full GitHub repository slug (e.g. 'owner/repo')."""
    if env is None:
        env = get_github_env()
    owner = get_github_owner(env)
    target = target_repo or os.environ.get("GITHUB_OUTPUT_REPO") or GITHUB_OUTPUT_REPO or ""
    if "/" in target:
        return target
    if target:
        return f"{owner}/{target}"
    return f"{owner}/remote-code-agent"


def get_authenticated_repo_url(full_repo: str, env: dict[str, str] | None = None) -> str:
    """Returns an authenticated git remote URL if GH_TOKEN or GITHUB_TOKEN is available."""
    if env is None:
        env = get_github_env()
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        return f"https://x-access-token:{token}@github.com/{full_repo}.git"
    return f"https://github.com/{full_repo}.git"


def sanitize_git_output(text: str) -> str:
    """Strips sensitive tokens from git command outputs."""
    if not text:
        return ""
    return re.sub(r"https://[^@]+@", "https://", text)


def list_user_github_repositories(env: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Lists all repositories for the authenticated user using GitHub CLI with API fallback."""
    if env is None:
        env = get_github_env()
    repos: list[dict[str, Any]] = []

    # 1. Try gh repo list with JSON format
    try:
        res = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                "--limit",
                "100",
                "--json",
                "name,description,url,updatedAt,visibility,isPrivate,isFork",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0 and res.stdout.strip():
            import json

            data = json.loads(res.stdout)
            if isinstance(data, list):
                return data
    except Exception:
        pass

    # 2. Try gh api user/repos
    try:
        res = subprocess.run(
            ["gh", "api", "user/repos?per_page=100&sort=updated", "--jq", "."],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0 and res.stdout.strip():
            import json

            data = json.loads(res.stdout)
            if isinstance(data, list):
                for item in data:
                    repos.append({
                        "name": item.get("name"),
                        "description": item.get("description") or "",
                        "url": item.get("html_url"),
                        "updatedAt": item.get("updated_at"),
                        "visibility": "PRIVATE" if item.get("private") else "PUBLIC",
                        "isPrivate": bool(item.get("private")),
                        "isFork": bool(item.get("fork")),
                    })
                return repos
    except Exception:
        pass

    # 3. Direct HTTP request with token fallback if gh command unavailable
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        try:
            import json
            import urllib.request

            req = urllib.request.Request(
                "https://api.github.com/user/repos?per_page=100&sort=updated",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "remote-code-agent",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list):
                    for item in data:
                        repos.append({
                            "name": item.get("name"),
                            "description": item.get("description") or "",
                            "url": item.get("html_url"),
                            "updatedAt": item.get("updated_at"),
                            "visibility": "PRIVATE" if item.get("private") else "PUBLIC",
                            "isPrivate": bool(item.get("private")),
                            "isFork": bool(item.get("fork")),
                        })
                    return repos
        except Exception:
            pass

    return repos


def push_to_dedicated_project_repo(
    project_dir: str,
    app_name: str,
    env: dict[str, str],
    target_repo: str | None = None,
) -> tuple[bool, str]:
    """Publishes project files directly to a dedicated GitHub repository named after the project (<owner>/<app_name>)."""
    owner = get_github_owner(env)
    project_repo = target_repo if target_repo else f"{owner}/{app_name}"

    # Check if repository exists on GitHub; create if missing
    view_res = subprocess.run(["gh", "repo", "view", project_repo], env=env, capture_output=True, text=True)
    if view_res.returncode != 0:
        create_res = subprocess.run(
            [
                "gh",
                "repo",
                "create",
                project_repo,
                "--public",
                "--description",
                f"{app_name} built autonomously by Antigravity CLI on Cloud",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if create_res.returncode == 0:
            time.sleep(2)  # Give GitHub API a moment to propagate newly created repository

    ignored_patterns = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".DS_Store", "node_modules"}

    # Ensure a basic .gitignore exists in project_dir
    gitignore_path = os.path.join(project_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("__pycache__/\n*.py[cod]\n.venv/\nvenv/\nnode_modules/\n.pytest_cache/\n.DS_Store\n")
        except Exception:
            pass

    repo_url = get_authenticated_repo_url(project_repo, env=env)
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = os.path.join(tmp_dir, "project-repo")
        clone_res = subprocess.run(["git", "clone", repo_url, repo_dir], env=env, capture_output=True, text=True)
        if clone_res.returncode != 0 or not os.path.exists(repo_dir):
            os.makedirs(repo_dir, exist_ok=True)
            subprocess.run(["git", "init"], cwd=repo_dir, env=env, check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=repo_dir, env=env, check=True)
        else:
            # Ensure origin remote URL uses authenticated repo_url
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=repo_dir, env=env, check=False)

        subprocess.run(["git", "config", "user.name", "Remote Code Agent"], cwd=repo_dir, env=env, check=True)
        subprocess.run(["git", "config", "user.email", "agent@remote-code-agent.local"], cwd=repo_dir, env=env, check=True)
        subprocess.run(["git", "checkout", "-B", "main"], cwd=repo_dir, env=env, check=True)

        # Copy generated files to root of the repo (excluding virtual environments and cache)
        for item in os.listdir(project_dir):
            if item in ignored_patterns:
                continue
            src = os.path.join(project_dir, item)
            dst = os.path.join(repo_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".venv", "venv", "__pycache__", ".pytest_cache", ".DS_Store", "node_modules"))
            else:
                shutil.copy2(src, dst)

        subprocess.run(["git", "add", "."], cwd=repo_dir, env=env, check=True)

        # Check if there are changes to commit
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir, env=env, capture_output=True, text=True)
        if status_res.stdout.strip():
            commit_msg = f"feat: build {app_name} autonomously with Antigravity CLI on Cloud"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_dir, env=env, check=True)
            push_res = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_dir, env=env, capture_output=True, text=True)
            if push_res.returncode != 0:
                push_res = subprocess.run(["git", "push", "--force", "-u", "origin", "main"], cwd=repo_dir, env=env, capture_output=True, text=True)
                if push_res.returncode != 0:
                    err_msg = (push_res.stderr or push_res.stdout or "unknown git error").strip()
                    sanitized_err = sanitize_git_output(err_msg)
                    if "workflow" in err_msg.lower():
                        return False, (
                            f"git push to {project_repo} failed: GitHub refused push because GH_TOKEN lacks the 'workflow' scope. "
                            f"Ensure your GitHub token has the 'workflow' scope enabled. Details: {sanitized_err}"
                        )
                    return False, f"git push to {project_repo} failed: {sanitized_err}"

        return True, f"https://github.com/{project_repo}"


def publish_project_to_github(
    project_dir: str,
    app_name: str,
    prompt: str = "",
    target_repo: str | None = None,
) -> tuple[bool, str]:
    """Publishes generated application files directly to main branch of target dedicated GitHub repository.

    1. Checks if project_dir contains files.
    2. Validates GitHub authentication.
    3. Ensures README.md exists inside the project directory.
    4. Pushes directly to dedicated repo (<owner>/<app_name> or target_repo).
    5. Returns the repository URL on success, or a descriptive error message on failure.
    """
    # Check if there are generated files (excluding hidden files)
    has_files = False
    for root, _, files in os.walk(project_dir):
        if ".git" in root:
            continue
        if any(not f.startswith(".") for f in files):
            has_files = True
            break

    if not has_files:
        return False, "No files were created in the project workspace."

    env = get_github_env()
    is_authed, auth_msg = check_github_auth(env)
    if not is_authed:
        return False, auth_msg

    ensure_git_config(env)

    # Ensure a README.md exists inside the project directory
    readme_path = os.path.join(project_dir, "README.md")
    if not os.path.exists(readme_path):
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(f"# {app_name}\n\nGenerated autonomously by Antigravity CLI on Cloud.\n")
        except Exception:
            pass

    return push_to_dedicated_project_repo(project_dir, app_name, env=env, target_repo=target_repo)
