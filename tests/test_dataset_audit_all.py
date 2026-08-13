"""Multi-issue consolidated dataset audit (the intake-seam fix, Option A).

`dataset_audit_all_discovered` runs the consolidated dataset audit for every discovered issue so each gets
a `scout_report_` under its own prefix (the artifact Edenseek intake ingests). The per-issue audit is mocked
here; these tests cover the orchestration contract: audit each issue, idempotent skip when the latest
consolidated report already covers the current revision, `force` override, and per-issue ISOLATION.
"""
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import dataset_auditor as da  # noqa: E402


class _Ctx:
    def __init__(self, prefix):
        self.scout_prefix = prefix


I1 = "publishers/edenseek/title_groups/caelaris/series/promises/issues/issue_001"
I2 = "publishers/edenseek/title_groups/i_ride_for_them/series/i_ride_for_them/issues/issue_001"


class TestDatasetAuditAllDiscovered(unittest.TestCase):
    def test_audits_each_issue_when_not_current(self):
        ctxs = [_Ctx(I1), _Ctx(I2)]
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(da.audit_s3_source, "resolve_current_revision",
                          return_value={"revision_id": "rev_A"}), \
             patch.object(da.scout_report_publisher, "last_published_revision_id", return_value=None), \
             patch.object(da, "run_dataset_audit", return_value={"quality_score": 0.9}) as run:
            result = da.dataset_audit_all_discovered()
        self.assertEqual(result["discovered"], 2)
        self.assertEqual(result["counts"], {"audited": 2})
        self.assertEqual(run.call_count, 2)
        self.assertEqual([r["issue_prefix"] for r in result["results"]], [I1, I2])
        # each issue is audited with its OWN context (the per-issue identity/write-path threading)
        self.assertEqual([c.kwargs.get("context") for c in run.call_args_list], ctxs)

    def test_skips_issue_already_covering_current_revision(self):
        with patch("scout_discovery.discover_contexts", return_value=[_Ctx(I1)]), \
             patch.object(da.audit_s3_source, "resolve_current_revision",
                          return_value={"revision_id": "rev_A"}), \
             patch.object(da.scout_report_publisher, "last_published_revision_id", return_value="rev_A"), \
             patch.object(da, "run_dataset_audit") as run:
            result = da.dataset_audit_all_discovered()
        self.assertEqual(result["counts"], {"skipped": 1})
        self.assertEqual(result["results"][0]["reason"], "already_current")
        run.assert_not_called()

    def test_force_reaudits_even_if_current(self):
        with patch("scout_discovery.discover_contexts", return_value=[_Ctx(I1)]), \
             patch.object(da.audit_s3_source, "resolve_current_revision",
                          return_value={"revision_id": "rev_A"}), \
             patch.object(da.scout_report_publisher, "last_published_revision_id", return_value="rev_A"), \
             patch.object(da, "run_dataset_audit", return_value={"quality_score": 0.8}) as run:
            result = da.dataset_audit_all_discovered(force=True)
        self.assertEqual(result["counts"], {"audited": 1})
        run.assert_called_once()

    def test_per_issue_failure_is_isolated_not_aborting(self):
        ctxs = [_Ctx(I1), _Ctx(I2)]
        with patch("scout_discovery.discover_contexts", return_value=ctxs), \
             patch.object(da.audit_s3_source, "resolve_current_revision",
                          side_effect=[RuntimeError("pointer gone"), {"revision_id": "rev_A"}]), \
             patch.object(da.scout_report_publisher, "last_published_revision_id", return_value=None), \
             patch.object(da, "run_dataset_audit", return_value={"quality_score": 0.9}) as run:
            result = da.dataset_audit_all_discovered()
        self.assertEqual(result["counts"], {"error": 1, "audited": 1})   # first errored, run continued
        self.assertEqual(result["results"][0]["status"], "error")
        run.assert_called_once()   # only the second issue reached run_dataset_audit


if __name__ == "__main__":
    unittest.main()
