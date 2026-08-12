"""Endpoint tests for SXI-2a multi-issue dashboard scoping.

Covers the new `GET /issues` picker source and the `issue_prefix` scoping added to
`/audit-review/archive`, `/audit-review/search`, `/reports/latest`, `/reports/{id}`. The underlying
discovery / archive / index reads are mocked (they would otherwise hit real S3); these tests pin the
endpoint contract: auth required, discovered issues projected with identity + prefix, a valid prefix is
resolved to a context and passed through, and a MALFORMED prefix is a 400 (client error), not a 503.
"""
import os
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

os.environ["SCOUT_USERNAME"] = "scout"
os.environ["SCOUT_PASSWORD"] = "testpass"

from fastapi.testclient import TestClient  # noqa: E402
import app as scout_app  # noqa: E402
import scout_discovery  # noqa: E402
import scout_archive  # noqa: E402
import scout_report_index  # noqa: E402
import scout_context  # noqa: E402

client = TestClient(scout_app.app)
AUTH = ("scout", "testpass")

PFX = "publishers/edenseek/title_groups/society_universe/series/i_ride_for_them/issues/issue_001"


def _ctx(prefix, series, issue):
    return SimpleNamespace(scout_prefix=prefix, identity={
        "publisher_id": "edenseek", "title_group_id": "society_universe",
        "series_id": series, "issue_id": issue})


class TestIssuesEndpoint(unittest.TestCase):
    def test_requires_auth(self):
        self.assertEqual(client.get("/issues").status_code, 401)

    def test_lists_discovered_issues_with_identity(self):
        ctxs = [_ctx(PFX, "i_ride_for_them", "issue_001"),
                _ctx("publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001",
                     "society_of_killers", "issue_001")]
        with patch.object(scout_discovery, "discover_contexts", return_value=ctxs):
            resp = client.get("/issues", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        issues = resp.json()["issues"]
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0]["issue_prefix"], PFX)
        self.assertEqual(issues[0]["series_id"], "i_ride_for_them")
        self.assertEqual(issues[0]["issue_id"], "issue_001")

    def test_discovery_failure_is_503(self):
        with patch.object(scout_discovery, "discover_contexts", side_effect=RuntimeError("no bucket")):
            resp = client.get("/issues", auth=AUTH)
        self.assertEqual(resp.status_code, 503)


class TestArchiveScoping(unittest.TestCase):
    def test_no_prefix_passes_context_none(self):
        with patch.object(scout_archive, "build_archive", return_value={"records": []}) as m:
            resp = client.get("/audit-review/archive", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(m.call_args.kwargs.get("context"))

    def test_valid_prefix_resolves_and_scopes(self):
        sentinel = object()
        with patch.object(scout_discovery, "context_for_prefix", return_value=sentinel) as mc, \
             patch.object(scout_archive, "build_archive", return_value={"records": []}) as mb:
            resp = client.get("/audit-review/archive", params={"issue_prefix": PFX}, auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        mc.assert_called_once_with(PFX)
        self.assertIs(mb.call_args.kwargs.get("context"), sentinel)

    def test_malformed_prefix_is_400_not_503(self):
        with patch.object(scout_discovery, "context_for_prefix",
                          side_effect=scout_context.IssueContextError("bad chain")), \
             patch.object(scout_archive, "build_archive", return_value={"records": []}) as mb:
            resp = client.get("/audit-review/archive", params={"issue_prefix": "garbage"}, auth=AUTH)
        self.assertEqual(resp.status_code, 400)
        mb.assert_not_called()   # never reached the archive read


class TestReportsScoping(unittest.TestCase):
    def test_latest_scopes_index_load(self):
        idx = {"latest": {"persisted_key": {"history": "k"}}, "entries": []}
        with patch.object(scout_discovery, "context_for_prefix", return_value=object()) as mc, \
             patch.object(scout_report_index, "load_index", return_value=idx) as mi, \
             patch.object(scout_app.scout_report_publisher, "read_object", return_value=b"{}"), \
             patch.object(scout_app.scout_report_publisher, "_s3_client", return_value=None):
            resp = client.get("/reports/latest", params={"issue_prefix": PFX}, auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        mc.assert_called_once_with(PFX)
        self.assertIn("context", mi.call_args.kwargs)

    def test_report_by_id_malformed_prefix_is_400(self):
        with patch.object(scout_discovery, "context_for_prefix",
                          side_effect=scout_context.IssueContextError("bad")):
            resp = client.get("/reports/rep_x", params={"issue_prefix": "garbage"}, auth=AUTH)
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
