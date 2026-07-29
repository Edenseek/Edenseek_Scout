"""Reports Archive + server-side search tests (Increment 5)."""
import io
import json
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_report_publisher as srp  # noqa: E402
import scout_archive as sa  # noqa: E402
import scout_context  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

PREFIX = "publishers/edenseek/title_groups/tg/series/soc/issues/issue_001"


class FakeS3:
    def __init__(self):
        self.store = {}

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)]), "VersionId": "v"}


def _entry(run_seq, *, precision, unchanged=0.9, gkey="cmp_g1", codes=None, wcount=1,
           findings=None, published="rev_pub"):
    return {
        "run_seq": run_seq, "report_id": f"scoutdelta::issue_001::{published}::run{run_seq:06d}",
        "run_id": f"run_{run_seq}", "issue_id": "issue_001", "publisher_id": "edenseek", "series_id": "soc",
        "completed_at": f"2026-07-2{run_seq}T00:00:00Z", "measurement_time": f"2026-07-2{run_seq}T00:00:00Z",
        "event_time": f"2026-07-1{run_seq}T00:00:00Z", "certified_at": "2026-07-27T00:00:00Z",
        "geometry_comparability_key": gkey, "metadata_comparability_key": "cmp_m1",
        "metrics": {"precision": precision, "recall": 0.6},
        "metadata_metrics": {"unchanged_metadata_rate": unchanged, "applicable": True},
        "finding_codes": codes if codes is not None else ["evidence.loaded"],
        "finding_counts": {"PASS": 3, "WARNING": wcount, "FAIL": 0, "INFO": 2},
        "worst_severity": "WARNING" if wcount else "PASS",
        "findings": findings or [{"code": "metadata.comparability", "severity": "WARNING",
                                  "title": "Metadata delta abstained", "detail": "schema-version skew"}],
        "published_revision_id": published, "generated_snapshot_revision_id": "rev_gen",
        "review_id": "rev_pub_12", "schema_version": "rr:v1|pa:v1|gs:-", "algorithm_version": "v1",
        "publisher_commit": "pubc0mmit", "scout_commit": "scoutc0mmit",
    }


def _index(entries, latest_seq):
    return {"report_index_version": "v1", "issue_prefix": PREFIX,
            "latest": {"run_seq": latest_seq}, "count": len(entries), "entries": entries}


def _ledger(failed_rev="rev_bad"):
    return {"revision_ledger_version": "v1", "issue_prefix": PREFIX, "count": 1,
            "entries": {f"{failed_rev}@fp_x": {
                "revision_id": failed_rev, "context_fingerprint": "fp_x", "status": "failed",
                "failure_stage": "persist_verify", "error_codes": ["ScoutReportPublishError"],
                "attempts": 2, "trigger": "event", "updated_at": "2026-07-26T12:00:00Z"}}}


class _Base(unittest.TestCase):
    def _s3(self, entries, latest_seq, ledger=True, gkeys=None):
        s3 = FakeS3()
        s3.store[("edenseek-scout", f"{PREFIX}/reports/report_index.json")] = \
            json.dumps(_index(entries, latest_seq)).encode()
        if ledger:
            s3.store[("edenseek-scout", f"{PREFIX}/ledger/processed_revisions.json")] = \
                json.dumps(_ledger()).encode()
        return s3

    def build(self, s3):
        with mock.patch.dict("os.environ", {srp.BUCKET_ENV: "edenseek-scout",
                                            srp.PREFIX_ENV: PREFIX, srp.REGION_ENV: "us-west-2"},
                             clear=False):
            return sa.build_archive(client=s3)


class TestArchive(_Base):
    def test_marks_and_ordering_and_boundary(self):
        e2 = _entry(2, precision=0.6, gkey="cmp_gB")   # newest, different geometry methodology
        e1 = _entry(1, precision=0.9, gkey="cmp_gA")
        arc = self.build(self._s3([e2, e1], latest_seq=2))
        self.assertEqual(arc["report_count"], 2)
        self.assertEqual(arc["failed_count"], 1)
        # newest first: failed run (2026-07-26) sits by its updated_at; reports at 07-22 / 07-21
        kinds = [r["record_kind"] for r in arc["records"]]
        self.assertIn("failed_run", kinds)
        reports = [r for r in arc["records"] if r["record_kind"] == "report"]
        self.assertTrue(reports[0]["is_latest"])          # run_seq 2 is latest
        self.assertTrue(reports[1]["is_historical"])
        # methodology boundary flagged on the older report (its geometry key differs from the newer)
        self.assertTrue(reports[1]["methodology_boundary"]["geometry"])
        self.assertFalse(reports[0]["methodology_boundary"]["geometry"])

    def test_failed_run_recorded(self):
        arc = self.build(self._s3([_entry(1, precision=0.9)], latest_seq=1))
        failed = [r for r in arc["records"] if r["record_kind"] == "failed_run"][0]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["failure_stage"], "persist_verify")
        self.assertEqual(failed["published_revision_id"], "rev_bad")


class TestSearch(_Base):
    def setUp(self):
        self.arc = self.build(self._s3(
            [_entry(2, precision=0.6, codes=["geometry.false_panels"], published="rev_B"),
             _entry(1, precision=0.9, codes=["evidence.loaded"], wcount=0, published="rev_A")],
            latest_seq=2))

    def test_metric_range(self):
        r = sa.search_archive(self.arc, "precision<0.80")
        self.assertEqual([x["run_seq"] for x in r["records"]], [2])   # only 0.6 < 0.80

    def test_metadata_unchanged_alias(self):
        r = sa.search_archive(self.arc, "metadata_unchanged_rate>=0.90")
        self.assertEqual(len(r["records"]), 2)                        # both 0.9

    def test_finding_and_severity(self):
        self.assertEqual([x["run_seq"] for x in
                          sa.search_archive(self.arc, "finding:geometry.false_panels")["records"]], [2])
        self.assertEqual([x["run_seq"] for x in
                          sa.search_archive(self.arc, "severity:WARNING")["records"]], [2])  # only run 2 has WARNING

    def test_field_filters_and_text(self):
        self.assertEqual(len(sa.search_archive(self.arc, "publisher:edenseek issue:issue_001")["records"]), 2)
        self.assertEqual([x["run_seq"] for x in sa.search_archive(self.arc, "revision:rev_B")["records"]], [2])
        self.assertEqual(len(sa.search_archive(self.arc, "schema")["records"]), 2)   # recommendation text
        self.assertEqual(len(sa.search_archive(self.arc, "commit:scoutc0mmit")["records"]), 2)

    def test_kind_and_metric_excludes_failed(self):
        self.assertEqual([r["record_kind"] for r in
                          sa.search_archive(self.arc, "kind:failed_run")["records"]], ["failed_run"])
        # a metric range naturally excludes failed runs (no metrics)
        self.assertTrue(all(r["record_kind"] == "report"
                            for r in sa.search_archive(self.arc, "precision>0")["records"]))


class TestParse(unittest.TestCase):
    def test_parse_query(self):
        f = sa.parse_query("precision<0.80 finding:geometry.false_panels severity:warning publisher:x foo")
        self.assertEqual(f["ranges"], [("precision", "<", 0.80)])
        self.assertEqual(f["findings"], ["geometry.false_panels"])
        self.assertEqual(f["severities"], ["WARNING"])
        self.assertEqual(f["fields"]["publisher"], "x")
        self.assertEqual(f["texts"], ["foo"])


class TestArchiveIssueContextThreading(_Base):
    """Increment 5b: build_archive forwards an explicit IssueContext to load_index + load_ledger,
    producing the identical archive with the environment cleared (context-driven)."""

    def _ctx(self):
        return scout_context.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix=PREFIX + "/approved",
            scout_bucket="edenseek-scout", scout_prefix=PREFIX)

    def test_build_archive_context_equals_env(self):
        s3 = self._s3([_entry(2, precision=0.8), _entry(1, precision=0.9)], latest_seq=2)
        arc_env = self.build(s3)
        with mock.patch.dict("os.environ", {}, clear=True):  # env cleared → context-driven
            arc_ctx = sa.build_archive(client=s3, context=self._ctx())
        self.assertEqual(arc_env, arc_ctx)
        self.assertEqual(arc_ctx["report_count"], 2)
        self.assertEqual(arc_ctx["failed_count"], 1)


if __name__ == "__main__":
    unittest.main()
