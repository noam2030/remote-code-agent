import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure src/ is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from remote_code_agent.project_service import (
    BASE_WORKSPACE,
    delete_project,
    get_project_details,
    list_local_projects,
    list_projects,
    parse_readme_projects,
    sanitize_project_name,
    sync_project_from_github,
)


class TestProjectService(unittest.TestCase):
    def test_sanitize_project_name(self):
        self.assertEqual(sanitize_project_name("My Super App"), "my-super-app")
        self.assertEqual(sanitize_project_name("hello_world_123"), "hello-world-123")
        self.assertEqual(sanitize_project_name("---App---Name---"), "app-name")
        self.assertEqual(sanitize_project_name("special!@#$%chars"), "specialchars")
        self.assertEqual(sanitize_project_name(""), "agent-app")

    def test_parse_readme_projects(self):
        readme = (
            "# Remote Code Agent Output\n\n"
            "## Projects\n"
            "- [hello-world-from-2052](https://hello-world-from-2052-wkczjb63na-uc.a.run.app) (Live Cloud Run App) | [Source Code](./hello-world-from-2052/)\n"
            "- [change-also-output-3836](https://change-also-output-3836-wkczjb63na-uc.a.run.app) (Live Cloud Run App) | [Source Code](./change-also-output-3836/)\n"
            "- [simple-app](./simple-app/): A simple sample project\n"
        )
        parsed = parse_readme_projects(readme)
        self.assertIn("hello-world-from-2052", parsed)
        self.assertEqual(
            parsed["hello-world-from-2052"]["cloud_run_url"],
            "https://hello-world-from-2052-wkczjb63na-uc.a.run.app",
        )
        self.assertIn("change-also-output-3836", parsed)
        self.assertEqual(
            parsed["change-also-output-3836"]["cloud_run_url"],
            "https://change-also-output-3836-wkczjb63na-uc.a.run.app",
        )
        self.assertIn("simple-app", parsed)

    def test_list_local_projects(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            proj1 = os.path.join(tmp_dir, "app-alpha")
            os.makedirs(proj1)
            with open(os.path.join(proj1, "main.py"), "w") as f:
                f.write("print('hello')")
            with open(os.path.join(proj1, "README.md"), "w") as f:
                f.write("# App Alpha")

            proj2 = os.path.join(tmp_dir, "app-beta")
            os.makedirs(proj2)
            with open(os.path.join(proj2, "index.html"), "w") as f:
                f.write("<h1>Beta</h1>")

            projects = list_local_projects(tmp_dir)
            self.assertIn("app-alpha", projects)
            self.assertIn("app-beta", projects)
            self.assertEqual(projects["app-alpha"]["files_count"], 2)
            self.assertIn("main.py", projects["app-alpha"]["files"])

    @patch("subprocess.run")
    def test_sync_project_from_github_success(self, mock_run):
        def mock_subprocess(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "clone" in cmd:
                clone_dest = cmd[-1]
                p_dir = os.path.join(clone_dest, "test-repo-app")
                os.makedirs(p_dir, exist_ok=True)
                with open(os.path.join(p_dir, "main.py"), "w") as f:
                    f.write("print('synced')")
            return m

        mock_run.side_effect = mock_subprocess

        with tempfile.TemporaryDirectory() as target_dir:
            success = sync_project_from_github("test-repo-app", target_dir)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(os.path.join(target_dir, "main.py")))

    @patch("remote_code_agent.project_service.list_remote_projects")
    def test_list_projects_combines_remote_and_local(self, mock_remote):
        mock_remote.return_value = {
            "remote-only-app": {
                "name": "remote-only-app",
                "github_url": "https://github.com/noam2030/remote-code-agent-output/tree/main/remote-only-app",
                "cloud_run_url": "https://remote-only-app.a.run.app",
                "has_remote": True,
            }
        }
        projects = list_projects()
        names = [p["name"] for p in projects]
        self.assertIn("remote-only-app", names)

    def test_delete_project_local_only(self):
        test_proj = "test-delete-local-app"
        proj_dir = os.path.join(BASE_WORKSPACE, test_proj)
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "app.py"), "w") as f:
            f.write("print('to be deleted')")

        self.assertTrue(os.path.exists(proj_dir))
        success, msg = delete_project(test_proj, delete_remote=False)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(proj_dir))
        self.assertIn("deleted from local workspace", msg)

    @patch("subprocess.run")
    def test_delete_project_remote_mocked(self, mock_run):
        def mock_subprocess(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "clone" in cmd:
                clone_dest = cmd[-1]
                p_dir = os.path.join(clone_dest, "mock-delete-app")
                os.makedirs(p_dir, exist_ok=True)
                readme_path = os.path.join(clone_dest, "README.md")
                with open(readme_path, "w") as f:
                    f.write("# Projects\n- [mock-delete-app](./mock-delete-app/)\n- [other-app](./other-app/)\n")
            return m

        mock_run.side_effect = mock_subprocess

        test_proj = "mock-delete-app"
        local_dir = os.path.join(BASE_WORKSPACE, test_proj)
        os.makedirs(local_dir, exist_ok=True)

        success, msg = delete_project(test_proj, delete_remote=True)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(local_dir))
        self.assertIn("successfully deleted", msg)


if __name__ == "__main__":
    unittest.main()
