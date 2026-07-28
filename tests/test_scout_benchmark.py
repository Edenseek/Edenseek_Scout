"""Benchmark projection tests (Increment 3) — the four invariants + hierarchy + rebuildability.

Weighted-from-counts (not mean-of-rates), sample size on every point/segment, methodology boundaries
(incompatible comparability keys never combined), dual event/measurement time ordering, and a
"no bare rate" invariant (every persisted metric carries numerator + denominator).
"""
import io
import json
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_report_publisher as srp  # noqa: E402
import scout_benchmark as sb  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

PUB = "publishers/edenseek/title_groups/tg/series/soc/issues"


def _geom(prec, recall, corrections=12, pages=6, gen=51, app=97):
    n_p, d_p = prec
    n_r, d_r = recall
    return {"ratios": {"precision": {"numerator": n_p, "denominator": d_p},
                       "recall": {"numerator": n_r, "denominator": d_r}},
            "total_human_geometry_corrections": corrections, "pages_evaluated": pages,
            "generated_panels_evaluated": gen, "approved_panels_evaluated": app}


def _meta(applicable=True, accepted=(5, 9), fields=9, arts=3, dist_sum=3.0):
    if not applicable:
        return {"applicable": False}
    n, d = accepted
    return {"applicable": True, "comparable_fields": fields, "comparable_artifacts": arts,
            "accepted_unchanged_rate": {"numerator": n, "denominator": d},
            "weighted_editorial_intervention_score": {"numerator": 3.0, "denominator": d},
            "corrections_per_artifact": {"numerator": 4, "denominator": arts},
            "revision_distance_sum": dist_sum}


def _entry(run_seq, *, geom_key="cmp_g1", meta_key="cmp_m1", geom=None, meta=None,
           event_time="2026-02-01T00:00:00Z", measurement_time="2026-02-01T00:00:00Z",
           issue_id="issue_001", geom_axes=None, meta_axes=None):
    return {
        "run_seq": run_seq, "report_id": f"r{run_seq}", "issue_id": issue_id,
        "publisher_id": "edenseek", "series_id": "soc",
        "event_time": event_time, "measurement_time": measurement_time,
        "certified_at": "2026-02-02T00:00:00Z",
        "geometry_comparability_key": geom_key, "metadata_comparability_key": meta_key,
        "comparability": {"geometry_axes": geom_axes or {"iou_threshold": 0.5},
                          "metadata_axes": meta_axes or {"metadata_revision_distance_version": "v1"}},
        "geometry_benchmark": geom if geom is not None else _geom((8, 10), (6, 10)),
        "metadata_benchmark": meta if meta is not None else _meta(),
    }


class TestInvariants(unittest.TestCase):
    def test_weighted_not_mean_of_rates(self):
        entries = [_entry(1, geom=_geom((8, 10), (6, 10))),
                   _entry(2, geom=_geom((90, 100), (50, 100)))]
        proj = sb.build_projection(entries, {"level": "issue"}, "2026-03-01T00:00:00Z")
        seg = proj["geometry"]["segments"]["cmp_g1"]
        # weighted: (8+90)/(10+100) = 0.890909, NOT the mean of rates (0.85)
        self.assertEqual(seg["metrics"]["precision"]["rate"], round(98 / 110, 6))
        self.assertNotEqual(seg["metrics"]["precision"]["rate"], round((0.8 + 0.9) / 2, 6))
        self.assertEqual(seg["metrics"]["precision"]["numerator"], 98)
        self.assertEqual(seg["metrics"]["precision"]["denominator"], 110)
        self.assertEqual(seg["sample_sizes"]["reports"], 2)
        self.assertEqual(seg["sample_sizes"]["pages"], 12)

    def test_no_bare_rate_every_point_and_segment_has_counts(self):
        entries = [_entry(1), _entry(2)]
        proj = sb.build_projection(entries, {"level": "issue"}, "t")
        for task in ("geometry", "metadata"):
            for p in proj[task]["points"]:
                self.assertIn("sample_sizes", p)
                self.assertIn("event_time", p)
                self.assertIn("measurement_time", p)
                for name, m in p["metrics"].items():
                    self.assertIsNotNone(m["numerator"], name)
                    self.assertIsNotNone(m["denominator"], name)
            for seg in proj[task]["segments"].values():
                self.assertIn("reports", seg["sample_sizes"])
                for m in seg["metrics"].values():
                    self.assertIn("numerator", m)
                    self.assertIn("denominator", m)

    def test_methodology_boundary_not_combined(self):
        entries = [_entry(1, geom_key="cmp_gA", geom_axes={"iou_threshold": 0.5}),
                   _entry(2, geom_key="cmp_gB", geom_axes={"iou_threshold": 0.6})]
        proj = sb.build_projection(entries, {"level": "issue"}, "t")
        self.assertEqual(set(proj["geometry"]["segments"]), {"cmp_gA", "cmp_gB"})   # not merged
        s = sb.series(proj, "geometry", "precision", order_by="measurement_time")
        self.assertEqual(len(s["boundaries"]), 1)
        self.assertEqual(s["boundaries"][0]["changed_axes"]["iou_threshold"], {"from": 0.5, "to": 0.6})

    def test_dual_time_ordering(self):
        # event order (B,C,A) differs from measurement order (A,B,C)
        A = _entry(3, event_time="2026-03-01T00:00:00Z", measurement_time="2026-01-01T00:00:00Z")
        B = _entry(1, event_time="2026-01-01T00:00:00Z", measurement_time="2026-02-01T00:00:00Z")
        C = _entry(2, event_time="2026-02-01T00:00:00Z", measurement_time="2026-03-01T00:00:00Z")
        proj = sb.build_projection([A, B, C], {"level": "issue"}, "t")
        by_event = [p["report_id"] for p in sb.series(proj, "geometry", "precision", "event_time")["points"]]
        by_meas = [p["report_id"] for p in sb.series(proj, "geometry", "precision", "measurement_time")["points"]]
        self.assertEqual(by_event, ["r1", "r2", "r3"])       # B, C, A by publication time
        self.assertEqual(by_meas, ["r3", "r1", "r2"])        # A, B, C by measurement time
        self.assertNotEqual(by_event, by_meas)

    def test_abstained_metadata_excluded(self):
        entries = [_entry(1, meta=_meta(applicable=False)), _entry(2, meta=_meta())]
        proj = sb.build_projection(entries, {"level": "issue"}, "t")
        self.assertEqual([p["run_seq"] for p in proj["metadata"]["points"]], [2])   # only the comparable one
        self.assertEqual([p["run_seq"] for p in proj["geometry"]["points"]], [1, 2])


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self.store[(Bucket, Key)] = Body if isinstance(Body, bytes) else Body.encode()
        return {"VersionId": "v"}

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)]), "VersionId": "v"}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = [k for (b, k) in self.store if b == Bucket and k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in sorted(keys)], "IsTruncated": False}


class TestHierarchy(unittest.TestCase):
    def _seed(self, s3):
        # two issues of the same series/publisher, each with one report entry
        idx1 = {"entries": [_entry(1, issue_id="issue_001", geom=_geom((8, 10), (6, 10)))]}
        idx2 = {"entries": [_entry(1, issue_id="issue_002", geom=_geom((90, 100), (50, 100)))]}
        s3.store[("edenseek-scout", f"{PUB}/issue_001/reports/report_index.json")] = json.dumps(idx1).encode()
        s3.store[("edenseek-scout", f"{PUB}/issue_002/reports/report_index.json")] = json.dumps(idx2).encode()

    def test_rebuild_hierarchy_weighted_platform(self):
        s3 = FakeS3()
        self._seed(s3)
        with mock.patch.dict("os.environ", {srp.BUCKET_ENV: "edenseek-scout"}, clear=False):
            written = sb.rebuild_all(client=s3, generated_at="t1")
            self.assertEqual(len(written["issue"]), 2)
            self.assertEqual(len(written["series"]), 1)
            self.assertEqual(len(written["publisher"]), 1)
            platform = sb.load_projection("benchmark/platform.json", client=s3)
        # platform precision weighted across both issues: (8+90)/(10+100)
        seg = platform["geometry"]["segments"]["cmp_g1"]
        self.assertEqual(seg["metrics"]["precision"]["rate"], round(98 / 110, 6))
        self.assertEqual(platform["sample_sizes"]["issues"], 2)
        self.assertEqual(platform["sample_sizes"]["reports"], 2)
        self.assertEqual(seg["sample_sizes"]["approved_panels"], 194)

    def test_rebuild_is_idempotent(self):
        s3 = FakeS3()
        self._seed(s3)
        with mock.patch.dict("os.environ", {srp.BUCKET_ENV: "edenseek-scout"}, clear=False):
            sb.rebuild_all(client=s3, generated_at="t1")
            first = s3.store[("edenseek-scout", "benchmark/platform.json")]
            sb.rebuild_all(client=s3, generated_at="t1")
            self.assertEqual(s3.store[("edenseek-scout", "benchmark/platform.json")], first)


if __name__ == "__main__":
    unittest.main()
