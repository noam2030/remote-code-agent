import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from remote_code_agent.server import app


class TestApiRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_workspace = tempfile.mkdtemp(prefix="test_api_workspace_")

    def tearDown(self):
        shutil.rmtree(self.test_workspace, ignore_errors=True)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "remote-code-agent-backend")

    def test_cors_headers_present(self):
        response = self.client.options(
            "/api/projects",
            headers={
                "Origin": "https://my-app.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access-control-allow-origin", response.headers)

    def test_list_projects(self):
        with patch("remote_code_agent.server.list_projects") as mock_list:
            mock_list.return_value = [{"name": "sample-project", "lines_of_code": 150}]
            response = self.client.get("/api/projects")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), 1)
            self.assertEqual(response.json()[0]["name"], "sample-project")

    def test_get_project_detail_404(self):
        with patch("remote_code_agent.server.get_project_details", return_value=None):
            response = self.client.get("/api/projects/non-existent-app")
            self.assertEqual(response.status_code, 404)

    def test_get_project_file_success(self):
        with patch("remote_code_agent.server.get_project_file_content") as mock_get_file:
            mock_get_file.return_value = {
                "file_path": "main.py",
                "content": "print('hello')",
                "lines": 1,
                "size_bytes": 14,
                "is_binary": False,
            }
            response = self.client.get("/api/projects/my-app/files/main.py")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["file_path"], "main.py")
            self.assertEqual(data["lines"], 1)

    def test_delete_project_endpoint(self):
        with patch("remote_code_agent.server.delete_project") as mock_delete:
            mock_delete.return_value = (True, "Project 'test-app' deleted successfully")
            response = self.client.delete("/api/projects/test-app")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["project"], "test-app")


if __name__ == "__main__":
    unittest.main()
