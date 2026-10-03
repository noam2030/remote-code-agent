import os
import re
import shutil
import subprocess
import tempfile
import time

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


def publish_project_to_github(
    project_dir: str,
    app_name: str,
    prompt: str = "",
    target_repo: str | None = None,
) -> tuple[bool, str]:
    """Publishes generated application files directly to main branch of target GitHub repository.

    1. Checks if project_dir contains files.
    2. Validates GitHub authentication.
    3. Clones the central output repository.
    4. Initializes 'main' branch if repository is empty.
    5. Pulls latest 'main' to stay in sync.
    6. Copies generated files into '<app_name>/' in the repository.
    7. Updates the repository README index.
    8. Commits and pushes directly to 'main' on GitHub (no pull request).
    9. Returns the direct URL to the published project on main.
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
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# {app_name}\n\nGenerated autonomously by Google Antigravity Remote Code Agent.\n")

    # Resolve target repository full name (e.g. noam2030/remote-code-agent-output)
    target = target_repo or os.environ.get("GITHUB_OUTPUT_REPO") or GITHUB_OUTPUT_REPO or "remote-code-agent-output"
    if "/" in target:
        full_repo = target
    else:
        owner_res = subprocess.run(["gh", "api", "user", "-q", ".login"], env=env, capture_output=True, text=True)
        owner = owner_res.stdout.strip() if owner_res.returncode == 0 and owner_res.stdout.strip() else "noam2030"
        full_repo = f"{owner}/{target}"

    # Use a temporary directory to clone the output repository, branch, and push
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = os.path.join(tmp_dir, "output-repo")
        clone_res = subprocess.run(
            ["git", "clone", f"https://github.com/{full_repo}.git", repo_dir],
            env=env,
            capture_output=True,
            text=True,
        )

        if clone_res.returncode != 0:
            return False, f"Failed to clone repository {full_repo}: {clone_res.stderr.strip()}"

        # Configure repository-level git user
        subprocess.run(["git", "config", "user.name", "Remote Code Agent"], cwd=repo_dir, env=env, check=True)
        subprocess.run(["git", "config", "user.email", "agent@remote-code-agent.local"], cwd=repo_dir, env=env, check=True)

        # Check if the repository is newly created / empty
        head_check = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, env=env, capture_output=True)
        if head_check.returncode != 0:
            # Initialize main branch
            subprocess.run(["git", "checkout", "-b", "main"], cwd=repo_dir, env=env, check=True)
            root_readme = os.path.join(repo_dir, "README.md")
            with open(root_readme, "w", encoding="utf-8") as f:
                f.write(
                    "# Remote Code Agent Output\n\n"
                    "Central repository for software applications generated autonomously by "
                    "[Remote Code Agent](https://github.com/noam2030/remote-code-agent).\n\n"
                    "## Projects\n\n"
                )
            subprocess.run(["git", "add", "README.md"], cwd=repo_dir, env=env, check=True)
            subprocess.run(
                ["git", "commit", "-m", "chore: initialize remote-code-agent-output repository"],
                cwd=repo_dir,
                env=env,
                check=True,
            )
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_dir, env=env, check=True)
        # Ensure on main and up to date
        subprocess.run(["git", "checkout", "main"], cwd=repo_dir, env=env, check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=repo_dir, env=env, capture_output=True)

        # Copy generated application files into <app_name>/ directory
        target_app_dir = os.path.join(repo_dir, app_name)
        os.makedirs(target_app_dir, exist_ok=True)
        for item in os.listdir(project_dir):
            if item == ".git":
                continue
            src_item = os.path.join(project_dir, item)
            dst_item = os.path.join(target_app_dir, item)
            if os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
            else:
                shutil.copy2(src_item, dst_item)

        # Update root README index
        root_readme = os.path.join(repo_dir, "README.md")
        if os.path.exists(root_readme):
            with open(root_readme, "r", encoding="utf-8") as f:
                content = f.read()
            entry = f"- [{app_name}](./{app_name}/): Autonomous code generation"
            if entry not in content:
                with open(root_readme, "a", encoding="utf-8") as f:
                    f.write(f"{entry}\n")

        # Stage and commit directly to main
        subprocess.run(["git", "add", "."], cwd=repo_dir, env=env, check=True)
        commit_msg = f"feat({app_name}): add {app_name} generated by Remote Code Agent"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_dir, env=env, check=True)

        # Push directly to main branch on GitHub (no PR needed)
        push_res = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        if push_res.returncode != 0:
            return False, f"git push error: {push_res.stderr.strip()}"

        project_url = f"https://github.com/{full_repo}/tree/main/{app_name}"
        return True, project_url
