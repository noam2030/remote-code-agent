import unittest
from unittest.mock import patch
import os
import sys

# Ensure src/ is discoverable even without package installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient

import remote_code_agent
from remote_code_agent.server import app
import remote_code_agent.main as pkg_main
import main


class TestServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_package_exports(self):
        self.assertIs(remote_code_agent.app, app)
        self.assertTrue(hasattr(remote_code_agent, "__version__"))

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["service"], "Google Antigravity Agent Service")
        self.assertIn("workspace", data)
        self.assertIn("docs", data)

    def test_main_exports_server_app(self):
        self.assertIs(main.app, app)
        self.assertIs(pkg_main.app, app)

    def test_routes_configured(self):
        routes = [route.path for route in app.routes]
        self.assertIn("/", routes)
        self.assertIn("/ui", routes)
        self.assertIn("/api/projects", routes)
        self.assertIn("/api/projects/{project_name}", routes)
        self.assertIn("/run", routes)

    def test_root_html_negotiation(self):
        response = self.client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Remote Code Agent", response.text)
        self.assertIn("Select a project", response.text)

    def test_ui_endpoint(self):
        response = self.client.get("/ui")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Remote Code Agent", response.text)

    def test_api_projects_endpoint(self):
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_api_project_details_endpoint(self):
        response = self.client.get("/api/projects/test-project-sample")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "test-project-sample")
        self.assertIn("github_url", data)

    def test_run_empty_prompt_error(self):
        response = self.client.post("/run", json={"prompt": "  "})
        self.assertEqual(response.status_code, 400)

    @patch("remote_code_agent.server.generate_code_stream")
    def test_run_with_project_json_payload(self, mock_gen):
        async def fake_stream(prompt, project_name=None):
            yield f"Project: {project_name}, Prompt: {prompt}"

        mock_gen.side_effect = fake_stream
        response = self.client.post(
            "/run",
            json={"prompt": "Add healthcheck", "project": "hello-world-from-2052"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Project: hello-world-from-2052", response.text)
        self.assertIn("Prompt: Add healthcheck", response.text)

    @patch("remote_code_agent.server.delete_project")
    def test_delete_project_endpoint(self, mock_delete):
        mock_delete.return_value = (True, "Project 'test-app' deleted successfully.")
        response = self.client.delete("/api/projects/test-app")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["project"], "test-app")
        self.assertIn("deleted successfully", data["message"])

    @patch("remote_code_agent.server.delete_project")
    def test_delete_project_endpoint_failure(self, mock_delete):
        mock_delete.return_value = (False, "Git push failed.")
        response = self.client.delete("/api/projects/failed-app")
        self.assertEqual(response.status_code, 500)
        self.assertIn("Git push failed", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
