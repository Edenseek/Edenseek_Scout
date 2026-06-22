import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

os.environ["SCOUT_USERNAME"] = "scout"
os.environ["SCOUT_PASSWORD"] = "testpass"

from fastapi.testclient import TestClient  # noqa: E402
import app as scout_app  # noqa: E402

client = TestClient(scout_app.app)
AUTH = ("scout", "testpass")


class TestDashboard(unittest.TestCase):
    def test_requires_auth(self):
        self.assertEqual(client.get("/dashboard").status_code, 401)

    def test_serves_intelligence_dashboard(self):
        resp = client.get("/dashboard", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Dataset Intelligence", html)
        # Legacy framing is gone.
        self.assertNotIn("always-on AI research agent", html.lower())

    def test_surfaces_required_screens(self):
        html = client.get("/dashboard", auth=AUTH).text
        for label in ("Daily Digest", "Review Queue", "Retrieval Readiness",
                      "Failure Analysis", "Reports Index"):
            self.assertIn(label, html)

    def test_reuses_existing_endpoints(self):
        html = client.get("/dashboard", auth=AUTH).text
        for endpoint in ("/audit/digest", "/audit/priority", "/audit/retrieval-readiness",
                         "/audit/failures", "/audit/reports", "/run-audit"):
            self.assertIn(endpoint, html)


if __name__ == "__main__":
    unittest.main()
