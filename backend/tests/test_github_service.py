import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure src/ is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from remote_code_agent.config import load_env_file, GITHUB_OUTPUT_REPO
from remote_code_agent.github_service import (
    check_github_auth,
    derive_project_slug,
    ensure_git_config,
    get_authenticated_repo_url,
    get_github_env,
    publish_project_to_github,
    sanitize_git_output,
)


class TestGithubService(unittest.TestCase):
    def test_load_env_file(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("# Sample env\nTEST_VAR_XYZ=hello_world\nGH_TOKEN_TEST=gho_12345\n")
            f_path = f.name

        try:
            load_env_file(f_path)
            self.assertEqual(os.environ.get("TEST_VAR_XYZ"), "hello_world")
            self.assertEqual(os.environ.get("GH_TOKEN_TEST"), "gho_12345")
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)
            os.environ.pop("TEST_VAR_XYZ", None)
            os.environ.pop("GH_TOKEN_TEST", None)

    def test_get_github_env_with_token(self):
        with patch.dict(os.environ, {"GH_TOKEN": "gho_sample_token"}, clear=False):
            env = get_github_env()
            self.assertEqual(env.get("GH_TOKEN"), "gho_sample_token")
            self.assertEqual(env.get("GITHUB_TOKEN"), "gho_sample_token")

    def test_check_github_auth_with_env_token(self):
        env = {"GH_TOKEN": "gho_mocked_token"}
        is_authed, msg = check_github_auth(env)
        self.assertTrue(is_authed)
        self.assertIn("GH_TOKEN", msg)

    @patch("subprocess.run")
    def test_check_github_auth_unauthenticated(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_run.return_value = mock_res

        env = {}
        is_authed, msg = check_github_auth(env)
        self.assertFalse(is_authed)
        self.assertIn("GitHub authentication missing", msg)

    def test_derive_project_slug(self):
        slug = derive_project_slug("Build a calculator app named math_genius")
        self.assertTrue(slug.startswith("math-genius-"))

    def test_publish_project_no_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            success, msg = publish_project_to_github(tmp_dir, "empty-repo")
            self.assertFalse(success)
            self.assertIn("No files were created", msg)

    def test_default_output_repo(self):
        self.assertEqual(GITHUB_OUTPUT_REPO, "")

    @patch("subprocess.run")
    def test_publish_project_to_github_mocked_flow(self, mock_run):
        # Mock subprocess run to simulate successful git clone, commit, and push directly to dedicated repo
        def mock_subprocess(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "api" in cmd and "user" in cmd:
                m.stdout = "testuser\n"
            elif "status" in cmd and "--porcelain" in cmd:
                m.stdout = "A  app.py\n"
            else:
                m.stdout = ""
                m.stderr = ""
            return m

        mock_run.side_effect = mock_subprocess

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a sample generated file
            with open(os.path.join(tmp_dir, "app.py"), "w") as f:
                f.write("print('hello')")

            with patch.dict(os.environ, {"GH_TOKEN": "gho_test_token"}):
                success, info = publish_project_to_github(
                    tmp_dir,
                    "test-app-1234",
                    prompt="Create a test app",
                )
                self.assertTrue(success)
                self.assertEqual(info, "https://github.com/testuser/test-app-1234")

    def test_get_authenticated_repo_url(self):
        url_with_token = get_authenticated_repo_url("owner/repo", env={"GH_TOKEN": "my-secret-token"})
        self.assertEqual(url_with_token, "https://x-access-token:my-secret-token@github.com/owner/repo.git")

        url_no_token = get_authenticated_repo_url("owner/repo", env={})
        self.assertEqual(url_no_token, "https://github.com/owner/repo.git")

    def test_sanitize_git_output(self):
        raw = "fatal: could not read from 'https://x-access-token:gho_12345secret@github.com/owner/repo.git'"
        sanitized = sanitize_git_output(raw)
        self.assertEqual(sanitized, "fatal: could not read from 'https://github.com/owner/repo.git'")
        self.assertNotIn("gho_12345secret", sanitized)
        self.assertEqual(sanitize_git_output(""), "")


    @patch("subprocess.run")
    def test_push_to_dedicated_repo_creates_gitignore_and_ignores_venv(self, mock_run):
        from remote_code_agent.github_service import push_to_dedicated_project_repo

        copied_items = []
        def mock_subprocess(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "api" in cmd and "user" in cmd:
                m.stdout = "testuser\n"
            elif "status" in cmd and "--porcelain" in cmd:
                m.stdout = "M app.py\n"
            else:
                m.stdout = ""
                m.stderr = ""
            return m

        mock_run.side_effect = mock_subprocess

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create files including a .venv dir and code file
            with open(os.path.join(tmp_dir, "app.py"), "w") as f:
                f.write("print('hello')")
            venv_dir = os.path.join(tmp_dir, ".venv")
            os.makedirs(venv_dir)
            with open(os.path.join(venv_dir, "env_lib.txt"), "w") as f:
                f.write("virtualenv")

            env = {"GH_TOKEN": "gho_test"}
            success, url = push_to_dedicated_project_repo(tmp_dir, "sample-project", env=env)
            self.assertTrue(success)
            self.assertEqual(url, "https://github.com/testuser/sample-project")
            # Verify .gitignore was created
            self.assertTrue(os.path.exists(os.path.join(tmp_dir, ".gitignore")))
            with open(os.path.join(tmp_dir, ".gitignore"), "r") as gf:
                content = gf.read()
                self.assertIn(".venv/", content)

    @patch("subprocess.run")
    def test_push_to_dedicated_repo_fails_cleanly_on_workflow_scope_rejection(self, mock_run):
        from remote_code_agent.github_service import push_to_dedicated_project_repo

        def mock_subprocess(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "api" in cmd and "user" in cmd:
                m.stdout = "testuser\n"
            elif "status" in cmd and "--porcelain" in cmd:
                m.stdout = "A  app.py\n"
            elif "push" in cmd:
                m.returncode = 1
                m.stderr = "remote rejected: refusing to allow an OAuth App to create or update workflow without workflow scope"
            else:
                m.stdout = ""
                m.stderr = ""
            return m

        mock_run.side_effect = mock_subprocess

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "app.py"), "w") as f:
                f.write("print('hello')")
            wf_dir = os.path.join(tmp_dir, ".github", "workflows")
            os.makedirs(wf_dir, exist_ok=True)
            ci_file = os.path.join(wf_dir, "ci.yml")
            with open(ci_file, "w") as f:
                f.write("name: CI")

            env = {"GH_TOKEN": "gho_test"}
            success, msg = push_to_dedicated_project_repo(tmp_dir, "sample-project", env=env)
            self.assertFalse(success)
            self.assertIn("workflow", msg.lower())
            self.assertIn("Ensure your GitHub token has the 'workflow' scope enabled", msg)
            # Verify files were NOT deleted
            self.assertTrue(os.path.exists(ci_file))
            self.assertTrue(os.path.exists(os.path.join(tmp_dir, "app.py")))

    @patch("subprocess.run")
    def test_sync_project_repo_secrets_sets_available_secrets(self, mock_run):
        from remote_code_agent.github_service import sync_project_repo_secrets

        calls = []

        def mock_subprocess(cmd, **kwargs):
            calls.append(cmd)
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            m.stderr = ""
            return m

        mock_run.side_effect = mock_subprocess

        env = {
            "GH_TOKEN": "gho_test",
            "GCP_SA_KEY": '{"type": "service_account"}',
            "VERCEL_TOKEN": "v_test_token",
        }
        sync_project_repo_secrets("testuser/my-project", env=env)

        secret_commands = [c for c in calls if len(c) >= 4 and c[0] == "gh" and c[1] == "secret" and c[2] == "set"]
        secret_names = [c[3] for c in secret_commands]
        self.assertIn("GCP_SA_KEY", secret_names)
        self.assertIn("VERCEL_TOKEN", secret_names)


if __name__ == "__main__":
    unittest.main()

