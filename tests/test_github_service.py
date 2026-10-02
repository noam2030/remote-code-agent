import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure src/ is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from remote_code_agent.config import load_env_file
from remote_code_agent.github_service import (
    check_github_auth,
    derive_project_slug,
    ensure_git_config,
    get_github_env,
    publish_project_to_github,
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


if __name__ == "__main__":
    unittest.main()
