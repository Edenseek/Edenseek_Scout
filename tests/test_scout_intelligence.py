"""Geometry/Metadata Intelligence + JSON-Schema compatibility tests (Increment 4)."""
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("SCOUT_USERNAME", "scout")
os.environ.setdefault("SCOUT_PASSWORD", "testpass")

import io  # noqa: E402
import json  # noqa: E402
from unittest import mock  # noqa: E402
import scout_intelligence as si  # noqa: E402
import scout_benchmark as sb  # noqa: E402
import scout_registry as sreg  # noqa: E402
import scout_schema as ss  # noqa: E402
import scout_report_publisher as srp  # noqa: E402
import scout_context  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app as scout_app  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

INTEL_PREFIX = "publishers/edenseek/title_groups/tg/series/soc/issues/issue_001"

AUTH = ("scout", "testpass")
client = TestClient(scout_app.app)


def _geom(splits=6, merges=30, false=3, miss=4, spread=34, gen=51, app_p=97, pages=36, corr=43):
    return {"ratios": {"precision": {"numerator": 48, "denominator": gen},
                       "recall": {"numerator": 59, "denominator": app_p},
                       "split_rate": {"numerator": splits, "denominator": app_p},
                       "merge_rate": {"numerator": merges, "denominator": gen},
                       "false_rate": {"numerator": false, "denominator": gen},
                       "missing_rate": {"numerator": miss, "denominator": app_p},
                       "unchanged_geometry_rate": {"numerator": 1, "denominator": app_p}},
            "panel_splits": splits, "panel_merges": merges, "false_panels": false,
            "missing_page_panels": miss, "spread_missing_panels": spread,
            "generated_panels_evaluated": gen, "approved_panels_evaluated": app_p,
            "total_human_geometry_corrections": corr, "pages_evaluated": pages}


def _meta(accepted=(5, 9), fields=9, arts=3):
    n, d = accepted
    return {"applicable": True, "comparable_fields": fields, "comparable_artifacts": arts,
            "counts": {"accepted_unchanged": n, "minor_wording_edit": 1, "moderate_rewrite": 1,
                       "major_rewrite": 1, "complete_replacement": 1, "added": 0, "removed": 0,
                       "abstention": 0, "unsupported_schema": 0},
            "accepted_unchanged_rate": {"numerator": n, "denominator": d},
            "weighted_editorial_intervention_score": {"numerator": 3.0, "denominator": d},
            "corrections_per_artifact": {"numerator": 4, "denominator": arts},
            "revision_distance_sum": 3.0}


def _entry(run_seq, *, gkey="cmp_gA", giou=0.5, meas="2026-07-2", meta=None,
           prompt="p1", model="m1", mschema="v1.1/v1.1"):
    return {
        "run_seq": run_seq, "report_id": f"rep{run_seq}", "issue_id": "issue_001",
        "publisher_id": "edenseek", "series_id": "soc",
        "event_time": f"{meas}{run_seq}T00:00:00Z", "measurement_time": f"{meas}{run_seq}T00:00:00Z",
        "geometry_comparability_key": gkey, "metadata_comparability_key": "cmp_mA",
        "comparability": {"geometry_axes": {"iou_threshold": giou, "geometry_detector_version": "v1"},
                          "metadata_axes": {"metadata_prompt_version": prompt, "metadata_model": model,
                                            "metadata_schema_version": mschema}},
        "geometry_benchmark": _geom(),
        "metadata_benchmark": meta if meta is not None else {"applicable": False},
        "persisted_key": {"history": f"h{run_seq}"},
    }


class TestGeometryIntelligence(unittest.TestCase):
    def test_projection_and_schema(self):
        entries = [_entry(1, gkey="cmp_gA", giou=0.5), _entry(2, gkey="cmp_gA", giou=0.5),
                   _entry(3, gkey="cmp_gB", giou=0.6)]           # boundary
        gi = si.geometry_intelligence(entries, "2026-07-30T00:00:00Z")
        ss.assert_valid(gi, "geometry_intelligence")             # conforms to the shared contract
        self.assertEqual(gi["task"], "geometry")
        # recurring failure modes summed + ranked
        seg = next(s for s in gi["recurring_failure_modes"] if s["comparability_key"] == "cmp_gA")
        merges = next(m for m in seg["modes"] if m["mode"] == "panel_merges")
        self.assertEqual(merges["count"], 60)                    # 30+30 across two reports
        # version-correlated improvement across the boundary, naming the changed axis
        self.assertTrue(gi["version_correlated_improvements"])
        imp = gi["version_correlated_improvements"][0]
        self.assertIn("iou_threshold", imp["changed_axes"])
        self.assertIn("recall", imp["metric_deltas"])
        # advisory recommendation + governance
        self.assertTrue(any(r["code"] == "geometry.under_segmentation" for r in gi["recommendations"]))
        self.assertTrue(gi["governance"]["advisory_only"])


class TestMetadataIntelligence(unittest.TestCase):
    def test_projection_and_schema(self):
        entries = [_entry(1, meta=_meta()), _entry(2, meta=_meta(accepted=(4, 9)))]
        reports = {f"rep{i}": {"delta_report": {"metadata_benchmark": {"per_field": {
            "classification.tags": {"accepted_unchanged_rate": {"numerator": 1, "denominator": 2},
                                    "counts": {"major_rewrite": 1, "complete_replacement": 1}},
            "narrative.summary": {"accepted_unchanged_rate": {"numerator": 2, "denominator": 2},
                                  "counts": {}},
        }}}} for i in (1, 2)}
        mi = si.metadata_intelligence(entries, reports, "2026-07-30T00:00:00Z")
        ss.assert_valid(mi, "metadata_intelligence")
        self.assertEqual(mi["comparable_reports"], 2)
        # tags is the weak field (high edit rate); summary is strong
        self.assertEqual(mi["weak_fields"][0]["field"], "classification.tags")
        self.assertGreater(mi["weak_fields"][0]["edit_rate"], 0)
        # prompt/model/schema correlation grouped with counts preserved
        self.assertEqual(len(mi["prompt_model_schema_correlations"]), 1)
        self.assertIn("numerator", mi["prompt_model_schema_correlations"][0])
        # opportunity + advisory recommendation, governed
        self.assertTrue(any(o["field"] == "classification.tags" for o in mi["prompt_improvement_opportunities"]))
        self.assertTrue(mi["governance"]["advisory_only"])

    def test_abstained_metadata_yields_empty_but_valid(self):
        mi = si.metadata_intelligence([_entry(1)], {}, "t")     # metadata not applicable
        ss.assert_valid(mi, "metadata_intelligence")
        self.assertEqual(mi["comparable_reports"], 0)


class TestSchemaCompatibility(unittest.TestCase):
    def test_benchmark_and_index_conform(self):
        entries = [_entry(1), _entry(2)]
        proj = sb.build_projection(entries, {"level": "platform"}, "t")
        ss.assert_valid(proj, "benchmark_projection")
        index = {"report_index_version": "v1", "count": 2, "latest": {"run_seq": 2}, "entries": entries}
        for e in entries:                                        # index requires these keys
            e.setdefault("run_id", f"run_{e['run_seq']}")
            e.setdefault("completed_at", e["measurement_time"])
            e.setdefault("report_sha256", "x")
        ss.assert_valid(index, "report_index")

    def test_validator_catches_missing_required(self):
        with self.assertRaises(ss.SchemaError):
            ss.assert_valid({"task": "geometry"}, "geometry_intelligence")


class TestEndpoints(unittest.TestCase):
    def test_schemas_served(self):
        r = client.get("/schemas", auth=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("geometry_intelligence", r.json()["schemas"])
        s = client.get("/schemas/geometry_intelligence", auth=AUTH)
        self.assertEqual(s.status_code, 200)
        self.assertEqual(s.json()["title"], "Geometry Intelligence projection (v1)")
        self.assertEqual(client.get("/schemas/nope", auth=AUTH).status_code, 404)

    def test_intelligence_endpoints_graceful_without_s3(self):
        # unconfigured S3 -> 503 (not 500); read-only, never a write attempt
        for path in ("/intelligence/geometry", "/intelligence/metadata"):
            self.assertIn(client.get(path, auth=AUTH).status_code, (200, 503))

    def test_intelligence_requires_auth(self):
        self.assertEqual(client.get("/intelligence/geometry").status_code, 401)

    def test_registry_endpoints_serve_persisted_projection(self):
        known = sreg.build_registry([sreg.build_entry(
            issue_prefix="publishers/edenseek/title_groups/tg/series/soc/issues/issue_001",
            identity={"publisher_id": "edenseek", "title_group_id": "tg",
                      "series_id": "soc", "issue_id": "issue_001"},
            publication_state="edenseek_approved")], generated_at="t1")
        with mock.patch.object(sreg, "load_registry", return_value=known):
            r = client.get("/registry", auth=AUTH)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), known)                    # serves the persisted flat projection
            t = client.get("/registry/tree", auth=AUTH)
            self.assertEqual(t.status_code, 200)
            self.assertIn("edenseek", t.json())                  # pure D6 rollup view

    def test_registry_requires_auth(self):
        self.assertEqual(client.get("/registry").status_code, 401)
        self.assertEqual(client.get("/registry/tree").status_code, 401)

    def test_registry_graceful_without_s3(self):
        # unconfigured/absent -> 200 (empty) or 503; read-only, never a 500 / write attempt
        self.assertIn(client.get("/registry", auth=AUTH).status_code, (200, 503))

    def test_observability_health_endpoint(self):
        known = sreg.build_registry([sreg.build_entry(
            issue_prefix="publishers/edenseek/title_groups/tg/series/soc/issues/issue_001",
            identity={"publisher_id": "edenseek", "title_group_id": "tg",
                      "series_id": "soc", "issue_id": "issue_001"},
            published_revision_id="rev_x", review_id="rev_x", publication_state="edenseek_approved",
            audit={"audit_state": "audited", "run_seq": 3, "run_id": "r", "report_id": "rep"})],
            generated_at="t1")
        with mock.patch.object(sreg, "load_registry", return_value=known):
            r = client.get("/observability/health", auth=AUTH)
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertEqual(body["projection"], "issue_health")
            self.assertEqual(body["summary"], {"healthy": 1, "attention": 0, "unknown": 0, "total": 1})
            self.assertEqual(body["records"][0]["health"], "healthy")

    def test_observability_health_requires_auth(self):
        self.assertEqual(client.get("/observability/health").status_code, 401)

    def test_observability_health_graceful(self):
        self.assertIn(client.get("/observability/health", auth=AUTH).status_code, (200, 503))


class _IntelFakeS3:
    def __init__(self):
        self.store = {}

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)]), "VersionId": "v"}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = [k for (b, k) in self.store if b == Bucket and k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in sorted(keys)], "IsTruncated": False}


class TestIntelligenceIssueContextThreading(unittest.TestCase):
    """Increment 5c: the build_* wrappers forward an explicit IssueContext to load_index (both) and
    read_object (metadata), producing identical intelligence with the environment cleared."""

    ENV = {srp.BUCKET_ENV: "edenseek-scout", srp.PREFIX_ENV: INTEL_PREFIX, srp.REGION_ENV: "us-west-2"}

    def _ctx(self):
        return scout_context.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix=INTEL_PREFIX + "/approved",
            scout_bucket="edenseek-scout", scout_prefix=INTEL_PREFIX)

    def _s3(self, entries):
        s3 = _IntelFakeS3()
        idx = {"report_index_version": "v1", "issue_prefix": INTEL_PREFIX, "count": len(entries),
               "latest": {"run_seq": entries[-1]["run_seq"]}, "entries": entries}
        s3.store[("edenseek-scout", f"{INTEL_PREFIX}/reports/report_index.json")] = json.dumps(idx).encode()
        return s3

    def test_geometry_intelligence_context_equals_env(self):
        s3 = self._s3([_entry(1), _entry(2, gkey="cmp_gB", giou=0.6)])
        with mock.patch.dict(os.environ, self.ENV, clear=False):
            gi_env = si.build_geometry_intelligence(client=s3, generated_at="t1")
        with mock.patch.dict(os.environ, {}, clear=True):  # env cleared → context-driven
            gi_ctx = si.build_geometry_intelligence(client=s3, generated_at="t1", context=self._ctx())
        self.assertEqual(gi_env, gi_ctx)

    def test_metadata_intelligence_context_equals_env(self):
        # non-comparable metadata → read_object is skipped; exercises load_index forwarding.
        s3 = self._s3([_entry(1), _entry(2)])
        with mock.patch.dict(os.environ, self.ENV, clear=False):
            mi_env = si.build_metadata_intelligence(client=s3, generated_at="t1")
        with mock.patch.dict(os.environ, {}, clear=True):
            mi_ctx = si.build_metadata_intelligence(client=s3, generated_at="t1", context=self._ctx())
        self.assertEqual(mi_env, mi_ctx)

    def test_metadata_forwards_context_to_load_index_and_read_object(self):
        ctx = self._ctx()
        entry = _entry(1, meta=_meta())  # applicable + comparable_fields + persisted_key.history="h1"
        idx = {"report_index_version": "v1", "issue_prefix": INTEL_PREFIX, "count": 1,
               "latest": {"run_seq": 1}, "entries": [entry]}
        captured = {}

        def fake_load_index(client=None, context=None):
            captured["load"] = context
            return idx

        def fake_read_object(client, key, context=None):
            captured["read"] = context
            return b"{}"

        with mock.patch.object(si.sri, "load_index", side_effect=fake_load_index), \
                mock.patch.object(si.srp, "read_object", side_effect=fake_read_object), \
                mock.patch.object(si, "metadata_intelligence", return_value={"ok": True}):
            si.build_metadata_intelligence(client=object(), context=ctx)
        self.assertEqual(captured["load"], ctx)
        self.assertEqual(captured["read"], ctx)


if __name__ == "__main__":
    unittest.main()
