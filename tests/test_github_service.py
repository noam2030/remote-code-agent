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
        self.assertEqual(GITHUB_OUTPUT_REPO, "remote-code-agent-output")

    @patch("subprocess.run")
    def test_publish_project_to_github_mocked_flow(self, mock_run):
        # Mock subprocess run to simulate successful git clone, commit, and push directly to main
        def mock_subprocess(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "api" in cmd and "user" in cmd:
                m.stdout = "testuser\n"
            elif "rev-parse" in cmd:
                m.returncode = 0  # not empty
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
                    target_repo="remote-code-agent-output",
                )
                self.assertTrue(success)
                self.assertEqual(info, "https://github.com/testuser/remote-code-agent-output/tree/main/test-app-1234")

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


if __name__ == "__main__":
    unittest.main()
