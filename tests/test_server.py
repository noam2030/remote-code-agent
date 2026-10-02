import unittest
from fastapi.testclient import TestClient

from server import app
import main


class TestServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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

    def test_routes_configured(self):
        routes = [route.path for route in app.routes]
        self.assertIn("/", routes)
        self.assertIn("/run", routes)


if __name__ == "__main__":
    unittest.main()
