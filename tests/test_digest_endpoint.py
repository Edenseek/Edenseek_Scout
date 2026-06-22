import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Configure auth before importing app (credentials are read at import time).
os.environ["SCOUT_USERNAME"] = "scout"
os.environ["SCOUT_PASSWORD"] = "testpass"

from fastapi.testclient import TestClient  # noqa: E402
import app as scout_app  # noqa: E402

# Plain TestClient (no context manager) avoids triggering the startup scheduler.
client = TestClient(scout_app.app)
AUTH = ("scout", "testpass")


class TestDigestEndpoint(unittest.TestCase):
    def test_requires_auth(self):
        self.assertEqual(client.get("/audit/digest").status_code, 401)

    def test_returns_digest(self):
        resp = client.get("/audit/digest", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("digest", body)
        digest = body["digest"]
        for key in ("quality_score", "readiness", "review", "highest_leverage_failure", "report_links"):
            self.assertIn(key, digest)
        self.assertIn(digest["readiness"]["verdict"], ("ready", "partially_ready", "not_ready"))


if __name__ == "__main__":
    unittest.main()
