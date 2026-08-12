"""Increment 1 — multi-issue delta-audit orchestration (`audit_all_discovered` + `/run-delta-audit-all`).

The per-issue audit is unchanged and mocked here; these tests cover the orchestration contract: audit every
discovered issue, deterministic order, per-issue ISOLATION (one failure never aborts the run), aggregate
counts, and the online endpoint (auth + pass-through + 503 only on an orchestrator/discovery blow-up).
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

import scout_delta_audit as sda  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app as scout_app  # noqa: E402

client = TestClient(scout_app.app)
AUTH = ("scout", "testpass")


class _Ctx:
    """Minimal stand-in for an IssueContext (the orchestrator only reads `.scout_prefix`)."""
    def __init__(self, prefix):
        self.scout_prefix = prefix


class TestAuditAllDiscovered(unittest.TestCase):
    def test_audits_each_discovered_issue_in_order(self):
        ctxs = [_Ctx("publishers/edenseek/title_groups/tg1/series/s1/issues/i1"),
                _Ctx("publishers/edenseek/title_groups/tg2/series/s2/issues/i2")]
        per_issue = [{"status": "persisted", "run_seq": 1, "revision_id": "rev1"},
                     {"status": "skipped", "revision_id": "rev2", "reason": "already_processed"}]
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(sda, "audit_current_revision", side_effect=per_issue) as m:
            result = sda.audit_all_discovered()
        self.assertEqual(result["discovered"], 2)
        self.assertEqual(result["counts"], {"persisted": 1, "skipped": 1})
        self.assertEqual([r["issue_prefix"] for r in result["results"]],
                         [c.scout_prefix for c in ctxs])   # deterministic, discovery order
        self.assertEqual(m.call_count, 2)
        # each per-issue call got its own context (read/write isolation is the context's job)
        for call, ctx in zip(m.call_args_list, ctxs):
            self.assertIs(call.kwargs["context"], ctx)

    def test_per_issue_failure_is_isolated_not_aborting(self):
        ctxs = [_Ctx("i1"), _Ctx("i2"), _Ctx("i3")]
        # i1 raises (defensive path), i2 returns a normal failed status, i3 succeeds — all recorded, run continues
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(sda, "audit_current_revision",
                          side_effect=[RuntimeError("boom"),
                                       {"status": "failed", "stage": "persist", "error": "x"},
                                       {"status": "persisted", "run_seq": 3}]):
            result = sda.audit_all_discovered()
        self.assertEqual(result["discovered"], 3)
        self.assertEqual(result["results"][0]["status"], "error")       # isolated raise
        self.assertEqual(result["results"][0]["issue_prefix"], "i1")
        self.assertEqual(result["results"][1]["status"], "failed")      # per-issue failed status
        self.assertEqual(result["results"][2]["status"], "persisted")   # later issue still ran
        self.assertEqual(result["counts"], {"error": 1, "failed": 1, "persisted": 1})

    def test_no_issues_discovered(self):
        with patch("scout_discovery.discover_contexts", return_value=[]):
            result = sda.audit_all_discovered()
        self.assertEqual(result["discovered"], 0)
        self.assertEqual(result["results"], [])
        self.assertEqual(result["counts"], {})

    def test_force_and_trigger_passed_through(self):
        ctxs = [_Ctx("i1")]
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(sda, "audit_current_revision", return_value={"status": "persisted"}) as m:
            sda.audit_all_discovered(force=True, trigger="scheduled_all")
        self.assertTrue(m.call_args.kwargs["force"])
        self.assertEqual(m.call_args.kwargs["trigger"], "scheduled_all")


class TestRunDeltaAuditAllEndpoint(unittest.TestCase):
    def test_requires_auth(self):
        self.assertEqual(client.post("/run-delta-audit-all").status_code, 401)

    def test_returns_aggregate(self):
        agg = {"discovered": 2, "counts": {"persisted": 1, "skipped": 1},
               "results": [{"status": "persisted", "issue_prefix": "i1"},
                           {"status": "skipped", "issue_prefix": "i2"}], "trigger": "manual_all"}
        with patch.object(sda, "audit_all_discovered", return_value=agg) as m:
            resp = client.post("/run-delta-audit-all", auth=AUTH)
        m.assert_called_once()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["discovered"], 2)
        self.assertEqual(resp.json()["counts"]["persisted"], 1)

    def test_per_issue_failure_still_200(self):
        # an individual issue failing is data in `results`, NOT an endpoint error
        agg = {"discovered": 2, "counts": {"persisted": 1, "failed": 1},
               "results": [{"status": "failed", "issue_prefix": "i1"},
                           {"status": "persisted", "issue_prefix": "i2"}], "trigger": "manual_all"}
        with patch.object(sda, "audit_all_discovered", return_value=agg):
            resp = client.post("/run-delta-audit-all", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["counts"]["failed"], 1)

    def test_orchestrator_blowup_is_503(self):
        with patch.object(sda, "audit_all_discovered", side_effect=RuntimeError("discovery/config error")):
            resp = client.post("/run-delta-audit-all", auth=AUTH)
        self.assertEqual(resp.status_code, 503)


class TestPostAuditRebuild(unittest.TestCase):
    """SXI-2e: --all refreshes the derived Registry + benchmark projections after the audit (non-fatal)."""

    def _one_issue(self):
        return ([_Ctx("publishers/edenseek/title_groups/tg1/series/s1/issues/i1")],
                {"status": "persisted", "run_seq": 1})

    def test_rebuild_true_refreshes_registry_and_benchmarks(self):
        ctxs, per = self._one_issue()
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(sda, "audit_current_revision", return_value=per), \
             patch("scout_registry.rebuild_discovered") as reg, \
             patch("scout_benchmark.rebuild_all") as bench:
            result = sda.audit_all_discovered(rebuild=True)
        reg.assert_called_once()
        bench.assert_called_once()
        self.assertEqual(result["rebuild"], {"registry": "rebuilt", "benchmark": "rebuilt"})

    def test_rebuild_default_false_is_increment1_behavior(self):
        ctxs, per = self._one_issue()
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(sda, "audit_current_revision", return_value=per), \
             patch("scout_registry.rebuild_discovered") as reg, \
             patch("scout_benchmark.rebuild_all") as bench:
            result = sda.audit_all_discovered()   # default
        reg.assert_not_called()
        bench.assert_not_called()
        self.assertNotIn("rebuild", result)

    def test_rebuild_failure_is_non_fatal_and_recorded(self):
        ctxs, per = self._one_issue()
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(sda, "audit_current_revision", return_value=per), \
             patch("scout_registry.rebuild_discovered", side_effect=RuntimeError("s3 down")), \
             patch("scout_benchmark.rebuild_all") as bench:
            result = sda.audit_all_discovered(rebuild=True)
        self.assertTrue(result["rebuild"]["registry"].startswith("failed"))
        self.assertEqual(result["rebuild"]["benchmark"], "rebuilt")   # benchmark still ran (independent)
        self.assertEqual(result["counts"], {"persisted": 1})           # the audit result is intact
        bench.assert_called_once()

    def test_benchmark_failure_is_non_fatal_and_independent(self):
        # symmetric to the registry-fails case: benchmark raises -> registry still rebuilt, audit intact
        ctxs, per = self._one_issue()
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(sda, "audit_current_revision", return_value=per), \
             patch("scout_registry.rebuild_discovered") as reg, \
             patch("scout_benchmark.rebuild_all", side_effect=RuntimeError("bench down")):
            result = sda.audit_all_discovered(rebuild=True)
        self.assertEqual(result["rebuild"]["registry"], "rebuilt")
        self.assertTrue(result["rebuild"]["benchmark"].startswith("failed"))
        self.assertEqual(result["counts"], {"persisted": 1})
        reg.assert_called_once()

    def test_endpoint_opts_into_rebuild(self):
        agg = {"discovered": 1, "counts": {"persisted": 1}, "results": [], "trigger": "manual_all",
               "rebuild": {"registry": "rebuilt", "benchmark": "rebuilt"}}
        with patch.object(sda, "audit_all_discovered", return_value=agg) as m:
            resp = client.post("/run-delta-audit-all", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(m.call_args.kwargs.get("rebuild"))


if __name__ == "__main__":
    unittest.main()
