"""Endpoint tests for POST /run-delta-audit — the online trigger for the delta audit.

The audit itself is mocked (it would otherwise resolve/read real S3); these tests verify the
endpoint contract: auth required, results passed through verbatim, and failed/error -> 503. The
production-safety guard (ADR-0002) independently blocks real S3 under the test runner regardless.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

os.environ["SCOUT_USERNAME"] = "scout"
os.environ["SCOUT_PASSWORD"] = "testpass"

from fastapi.testclient import TestClient  # noqa: E402
import app as scout_app  # noqa: E402
import scout_delta_audit  # noqa: E402

client = TestClient(scout_app.app)
AUTH = ("scout", "testpass")


class TestRunDeltaAuditEndpoint(unittest.TestCase):
    def test_requires_auth(self):
        self.assertEqual(client.post("/run-delta-audit").status_code, 401)

    def test_persisted_run_passed_through(self):
        result = {"status": "persisted", "revision_id": "rev_b1470df6117a", "run_id": "run_x",
                  "run_seq": 7, "report_id": "rep_x", "index_count": 3, "trigger": "manual"}
        with patch.object(scout_delta_audit, "audit_current_revision", return_value=result) as m:
            resp = client.post("/run-delta-audit", auth=AUTH)
        m.assert_called_once()
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "persisted")
        self.assertEqual(body["run_seq"], 7)
        self.assertEqual(body["revision_id"], "rev_b1470df6117a")

    def test_skipped_is_a_200_noop(self):
        result = {"status": "skipped", "revision_id": "rev_b1470df6117a",
                  "reason": "already_processed", "run_seq": 7}
        with patch.object(scout_delta_audit, "audit_current_revision", return_value=result):
            resp = client.post("/run-delta-audit", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "skipped")

    def test_failed_is_503(self):
        result = {"status": "failed", "revision_id": "rev_x", "stage": "persist", "error": "Boom"}
        with patch.object(scout_delta_audit, "audit_current_revision", return_value=result):
            resp = client.post("/run-delta-audit", auth=AUTH)
        self.assertEqual(resp.status_code, 503)

    def test_error_is_503(self):
        result = {"status": "error", "stage": "resolve", "error": "no pointer"}
        with patch.object(scout_delta_audit, "audit_current_revision", return_value=result):
            resp = client.post("/run-delta-audit", auth=AUTH)
        self.assertEqual(resp.status_code, 503)

    def test_unexpected_exception_is_503(self):
        with patch.object(scout_delta_audit, "audit_current_revision", side_effect=RuntimeError("x")):
            resp = client.post("/run-delta-audit", auth=AUTH)
        self.assertEqual(resp.status_code, 503)


if __name__ == "__main__":
    unittest.main()
