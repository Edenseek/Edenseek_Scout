"""Tests for the Scout revision watcher (the automated trigger layer).

Covers: no-op when the Approved Dataset revision is unchanged (pointer read only,
no audit, no LLM), audit + publish when the revision changes, first-run (no prior
report) triggers an audit, idempotency across repeated polls, fail-loud on a
pointer/config error, and interval configurability. The audit pipeline itself is
mocked — this verifies only the trigger decision, keeping the two layers separate.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_watch  # noqa: E402
import audit_s3_source  # noqa: E402
import scout_report_publisher  # noqa: E402


class TestScoutWatch(unittest.TestCase):
    def _patch(self, current_rev, last_rev):
        """Patch the trigger's three seams and return the run_dataset_audit mock."""
        resolve = mock.patch.object(
            scout_watch.audit_s3_source, "resolve_current_revision",
            return_value={"revision_id": current_rev, "key": "k", "version_id": "v",
                          "revision_key": "rk"})
        last = mock.patch.object(
            scout_watch.scout_report_publisher, "last_published_revision_id",
            return_value=last_rev)
        audit = mock.patch.object(
            scout_watch.dataset_auditor, "run_dataset_audit",
            return_value={"quality_score": 74, "dataset_id": "society_of_killers/issue_001"})
        return resolve, last, audit

    def test_unchanged_revision_is_noop(self):
        resolve, last, audit = self._patch("rev_x", "rev_x")
        with resolve, last, audit as audit_mock:
            out = scout_watch.check_and_audit()
        self.assertEqual(out["status"], "unchanged")
        self.assertEqual(out["revision_id"], "rev_x")
        audit_mock.assert_not_called()  # no audit → no materialization, no LLM

    def test_changed_revision_triggers_audit(self):
        resolve, last, audit = self._patch("rev_new", "rev_old")
        with resolve, last, audit as audit_mock:
            out = scout_watch.check_and_audit()
        self.assertEqual(out["status"], "published")
        self.assertEqual(out["revision_id"], "rev_new")
        audit_mock.assert_called_once_with()

    def test_first_run_no_prior_report_triggers_audit(self):
        resolve, last, audit = self._patch("rev_first", None)
        with resolve, last, audit as audit_mock:
            out = scout_watch.check_and_audit()
        self.assertEqual(out["status"], "published")
        audit_mock.assert_called_once_with()

    def test_idempotent_after_publish(self):
        # First poll publishes; once the report records rev_new, the next poll (now
        # last == current) is a no-op.
        resolve, last, audit = self._patch("rev_new", "rev_old")
        with resolve, last, audit as audit_mock:
            scout_watch.check_and_audit()
            self.assertEqual(audit_mock.call_count, 1)
        resolve2, last2, audit2 = self._patch("rev_new", "rev_new")
        with resolve2, last2, audit2 as audit_mock2:
            out = scout_watch.check_and_audit()
        self.assertEqual(out["status"], "unchanged")
        audit_mock2.assert_not_called()

    def test_pointer_error_is_fail_loud(self):
        resolve = mock.patch.object(
            scout_watch.audit_s3_source, "resolve_current_revision",
            side_effect=audit_s3_source.ScoutS3SourceError("unreachable"))
        audit = mock.patch.object(scout_watch.dataset_auditor, "run_dataset_audit")
        with resolve, audit as audit_mock:
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                scout_watch.check_and_audit()
            audit_mock.assert_not_called()
        # Single-shot main() surfaces the failure as a non-zero exit.
        with mock.patch.object(scout_watch, "check_and_audit",
                               side_effect=audit_s3_source.ScoutS3SourceError("x")):
            self.assertEqual(scout_watch.main([]), 1)

    def test_single_shot_success_exits_zero(self):
        with mock.patch.object(scout_watch, "check_and_audit",
                               return_value={"status": "unchanged"}):
            self.assertEqual(scout_watch.main([]), 0)

    def test_interval_is_configurable(self):
        with mock.patch.dict("os.environ", {scout_watch.WATCH_INTERVAL_ENV: "45"}, clear=False):
            self.assertEqual(scout_watch._interval_seconds(), 45)
        with mock.patch.dict("os.environ", {scout_watch.WATCH_INTERVAL_ENV: "bad"}, clear=False):
            self.assertEqual(scout_watch._interval_seconds(), scout_watch.DEFAULT_INTERVAL_SECONDS)
        env = {k: v for k, v in __import__("os").environ.items() if k != scout_watch.WATCH_INTERVAL_ENV}
        with mock.patch.dict("os.environ", env, clear=True):
            self.assertEqual(scout_watch._interval_seconds(), scout_watch.DEFAULT_INTERVAL_SECONDS)


class TestLastPublishedRevision(unittest.TestCase):
    def _env(self):
        return {
            scout_report_publisher.BUCKET_ENV: "edenseek-scout",
            scout_report_publisher.PREFIX_ENV:
                "publishers/edenseek/title_groups/society_universe/series/"
                "society_of_killers/issues/issue_001",
            scout_report_publisher.REGION_ENV: "us-west-2",
        }

    def test_missing_report_returns_none(self):
        from botocore.exceptions import ClientError
        client = mock.Mock()
        client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        with mock.patch.dict("os.environ", self._env(), clear=False):
            self.assertIsNone(scout_report_publisher.last_published_revision_id(client=client))

    def test_returns_recorded_revision(self):
        import json as _json

        class _Body:
            def read(self):
                return _json.dumps(
                    {"provenance": {"publisher_revision_id": "rev_persisted"}}).encode()

        client = mock.Mock()
        client.get_object.return_value = {"Body": _Body()}
        with mock.patch.dict("os.environ", self._env(), clear=False):
            self.assertEqual(
                scout_report_publisher.last_published_revision_id(client=client),
                "rev_persisted")


if __name__ == "__main__":
    unittest.main()
