"""Increment 4c: optional IssueContext threading through the dataset_auditor runner.

Proves (a) the read seam (`_resolve_input_dir`) forwards context to
`materialize_approved_contract`, with context=None byte-for-byte the env path and explicit dirs
taking precedence; and (b) `run_dataset_audit` forwards context to the Scout-repo publication and
that the publication gate is `context is not None or is_configured()` — so a context opens the gate
even when the environment is unconfigured, while context=None leaves the gate exactly as before.
"""
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import dataset_auditor  # noqa: E402
import scout_context  # noqa: E402

FIXTURE_DIR = str(REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1")
REPO_PREFIX = ("publishers/edenseek/title_groups/society_universe/series/"
               "society_of_killers/issues/issue_001")


def _ctx():
    return scout_context.IssueContext.for_prefixes(
        approved_bucket="edenseek-publishing", approved_prefix=REPO_PREFIX + "/approved",
        scout_bucket="edenseek-scout", scout_prefix=REPO_PREFIX)


class TestResolveInputDirThreading(unittest.TestCase):
    def test_forwards_context_to_materialize(self):
        ctx = _ctx()
        with mock.patch.object(dataset_auditor.audit_s3_source,
                               "materialize_approved_contract", return_value="/materialized") as mat, \
                mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(dataset_auditor._resolve_input_dir(None, context=ctx), "/materialized")
            mat.assert_called_once_with(context=ctx)

    def test_context_none_is_env_path(self):
        with mock.patch.object(dataset_auditor.audit_s3_source,
                               "materialize_approved_contract", return_value="/materialized") as mat, \
                mock.patch.dict(os.environ, {}, clear=True):
            dataset_auditor._resolve_input_dir(None)
            mat.assert_called_once_with(context=None)  # byte-for-byte: same call as before

    def test_explicit_dir_wins_and_ignores_context(self):
        with mock.patch.object(dataset_auditor.audit_s3_source,
                               "materialize_approved_contract") as mat:
            self.assertEqual(dataset_auditor._resolve_input_dir("/explicit", context=_ctx()), "/explicit")
            mat.assert_not_called()


class TestRunDatasetAuditThreading(unittest.TestCase):
    """Drive the real scoring pipeline over the fixture, mocking only the side-effect writers and the
    Scout-repo publication boundary, so we can observe the gate + the context actually forwarded."""

    def _run_capturing(self, context, configured):
        cap = {}

        def cap_reports(result, generated_at, context=None):
            cap["reports"] = context
            return {}

        def cap_scout(result, generated_at, provenance=None, context=None):
            cap["scout"] = context
            return {"report_id": "rid"}

        da = dataset_auditor
        with mock.patch.object(da, "_resolve_input_dir", return_value=FIXTURE_DIR), \
                mock.patch.object(da.scout, "record_audit_history", return_value=[]), \
                mock.patch.object(da.scout, "update_dataset_memory"), \
                mock.patch.object(da, "_latest_delta", return_value=None), \
                mock.patch.object(da, "_retrieval_trend", return_value=None), \
                mock.patch.object(da.audit_history_analysis, "build_historical_intelligence",
                                  return_value={}), \
                mock.patch.object(da.audit_retrieval_readiness, "build_retrieval_readiness",
                                  return_value={}), \
                mock.patch.object(da.audit_digest, "build_digest", return_value={}), \
                mock.patch.object(da.audit_reports, "write_reports", return_value={}), \
                mock.patch.object(da.audit_s3_source, "load_source_provenance", return_value={}), \
                mock.patch.object(da.scout_report_publisher, "is_configured", return_value=configured), \
                mock.patch.object(da.scout_report_publisher, "publish_reports", side_effect=cap_reports), \
                mock.patch.object(da.scout_report_publisher, "publish_scout_report",
                                  side_effect=cap_scout), \
                mock.patch.dict(os.environ, {}, clear=True):
            da.run_dataset_audit(context=context)
        return cap

    def test_context_opens_gate_and_is_forwarded(self):
        # Environment unconfigured (is_configured=False) but a context is supplied -> publish anyway,
        # with the context forwarded to both publication calls.
        ctx = _ctx()
        cap = self._run_capturing(context=ctx, configured=False)
        self.assertEqual(cap.get("reports"), ctx)
        self.assertEqual(cap.get("scout"), ctx)

    def test_context_none_unconfigured_skips_publication(self):
        # context=None + is_configured()=False -> gate closed, exactly as before (byte-for-byte).
        cap = self._run_capturing(context=None, configured=False)
        self.assertNotIn("reports", cap)
        self.assertNotIn("scout", cap)

    def test_context_none_configured_publishes_with_none(self):
        # context=None + is_configured()=True -> publishes on the env path, forwarding context=None.
        cap = self._run_capturing(context=None, configured=True)
        self.assertIsNone(cap.get("reports"))
        self.assertIsNone(cap.get("scout"))
        self.assertIn("reports", cap)


if __name__ == "__main__":
    unittest.main()
