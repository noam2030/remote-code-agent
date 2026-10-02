import unittest
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
        self.assertIn("/run", routes)


if __name__ == "__main__":
    unittest.main()
