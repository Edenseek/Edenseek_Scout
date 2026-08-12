"""SXI-2c: cross-issue scoping — benchmark key derivation, scoped Intelligence loaders, and the
COMPARABILITY GUARD (entries produced under different methodologies are never averaged together, even
when aggregated across issues at a scope)."""
import io
import json
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

os.environ["SCOUT_USERNAME"] = "scout"
os.environ["SCOUT_PASSWORD"] = "testpass"

from botocore.exceptions import ClientError  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import scout_intelligence as si  # noqa: E402
import scout_report_publisher as srp  # noqa: E402
import scout_benchmark as sb  # noqa: E402
import app as scout_app  # noqa: E402

client = TestClient(scout_app.app)
AUTH = ("scout", "testpass")

PUB1 = "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues"
PUB2 = "publishers/edenseek/title_groups/i_ride_for_them/series/i_ride_for_them/issues"
# I4 is a LEADING-STRING SIBLING of society_of_killers (series `society_of_killers2`) under the SAME
# universe — the exact case that a `startswith(prefix)` filter WITHOUT the trailing "/" would wrongly include.
PUB4 = "publishers/edenseek/title_groups/society_universe/series/society_of_killers2/issues"
I1, I2, I3, I4 = f"{PUB1}/issue_001", f"{PUB1}/issue_002", f"{PUB2}/issue_001", f"{PUB4}/issue_001"
SOC_ROOT = "publishers/edenseek/title_groups/society_universe/series/society_of_killers"


def _geom():
    return {"ratios": {"precision": {"numerator": 8, "denominator": 10},
                       "recall": {"numerator": 6, "denominator": 10}},
            "total_human_geometry_corrections": 0, "pages_evaluated": 6,
            "generated_panels_evaluated": 10, "approved_panels_evaluated": 10}


def _entry(run_seq, gkey="cmp_gA", issue_id="issue_001", series_id="society_of_killers"):
    return {"run_seq": run_seq, "report_id": f"r{run_seq}_{series_id}_{issue_id}", "issue_id": issue_id,
            "publisher_id": "edenseek", "series_id": series_id,
            "event_time": "2026-02-01T00:00:00Z", "measurement_time": "2026-02-01T00:00:00Z",
            "certified_at": "2026-02-02T00:00:00Z",
            "geometry_comparability_key": gkey, "metadata_comparability_key": "cmp_mA",
            "comparability": {"geometry_axes": {"iou_threshold": 0.5},
                              "metadata_axes": {"metadata_revision_distance_version": "v1"}},
            "geometry_benchmark": _geom(), "metadata_benchmark": {"applicable": False}}


class FakeS3:
    def __init__(self):
        self.store = {}

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)]), "VersionId": "v"}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = [k for (b, k) in self.store if b == Bucket and k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in sorted(keys)], "IsTruncated": False}


def _seed(s3):
    # I1 (society_of_killers) has TWO entries with DIFFERENT geometry keys (a methodology change within the
    # issue); I2 is another society_of_killers issue; I3 is a different series (i_ride_for_them).
    s3.store[("edenseek-scout", f"{I1}/reports/report_index.json")] = json.dumps({"entries": [
        _entry(1, gkey="cmp_gA"), _entry(2, gkey="cmp_gB")]}).encode()
    s3.store[("edenseek-scout", f"{I2}/reports/report_index.json")] = json.dumps({"entries": [
        _entry(1, gkey="cmp_gA", issue_id="issue_002")]}).encode()
    s3.store[("edenseek-scout", f"{I3}/reports/report_index.json")] = json.dumps({"entries": [
        _entry(1, gkey="cmp_gA", series_id="i_ride_for_them")]}).encode()
    # society_of_killers2 — shares the SOC_ROOT string as a prefix; must be excluded by the `+ "/"` boundary.
    s3.store[("edenseek-scout", f"{I4}/reports/report_index.json")] = json.dumps({"entries": [
        _entry(1, gkey="cmp_gA", series_id="society_of_killers2")]}).encode()
    return s3


class TestScopeAndPrefix(unittest.TestCase):
    def test_each_level(self):
        self.assertEqual(si._scope_and_prefix("platform", ""), ({"level": "platform"}, ""))
        self.assertEqual(si._scope_and_prefix("issue", I1), (
            {"level": "issue", "publisher_id": "edenseek", "title_group_id": "society_universe",
             "series_id": "society_of_killers", "issue_id": "issue_001"}, I1))
        self.assertEqual(si._scope_and_prefix("series", I1)[1], SOC_ROOT)
        self.assertEqual(si._scope_and_prefix("publisher", I1)[1], "publishers/edenseek")

    def test_bad_level_and_prefix(self):
        with self.assertRaises(ValueError):
            si._scope_and_prefix("galaxy", I1)
        with self.assertRaises((KeyError, IndexError)):
            si._scope_and_prefix("series", "publishers/edenseek")   # not an issue chain


class TestScopedEntries(unittest.TestCase):
    def test_filtering_by_scope(self):
        s3 = _seed(FakeS3())
        self.assertEqual(len(si._scoped_entries(s3, "edenseek-scout", "")[0]), 5)              # platform: all
        self.assertEqual(len(si._scoped_entries(s3, "edenseek-scout", SOC_ROOT)[0]), 3)         # series: I1(2)+I2(1)
        self.assertEqual(len(si._scoped_entries(s3, "edenseek-scout", I1)[0]), 2)               # issue: only I1
        self.assertEqual(len(si._scoped_entries(s3, "edenseek-scout", "publishers/edenseek")[0]), 5)  # publisher

    def test_prefix_is_boundary_safe(self):
        # The `+ "/"` boundary: a series scope for `society_of_killers` must NOT swallow the leading-string
        # sibling `society_of_killers2` (I4). Without the trailing "/", startswith would leak it -> 4 entries.
        s3 = _seed(FakeS3())
        soc = si._scoped_entries(s3, "edenseek-scout", SOC_ROOT)[0]
        self.assertEqual(len(soc), 3)                                        # I1(2)+I2(1) only
        self.assertNotIn("society_of_killers2", {e["series_id"] for e in soc})
        self.assertTrue(all(e["series_id"] == "society_of_killers" for e in soc))


class TestComparabilityGuard(unittest.TestCase):
    def test_different_keys_never_averaged_across_issues(self):
        # THE guard: aggregating platform-wide, cmp_gA (I1+I2+I3 = 3 reports) and cmp_gB (I1 = 1 report) must
        # remain SEPARATE segments — never combined into one averaged number.
        s3 = _seed(FakeS3())
        with mock.patch.dict(os.environ, {srp.BUCKET_ENV: "edenseek-scout"}, clear=False):
            proj = si.build_geometry_intelligence_scoped(level="platform", client=s3)
        self.assertEqual(proj["sample_sizes"]["reports"], 5)
        self.assertEqual(proj["sample_sizes"]["segments"], 2)               # NOT 1 — keys kept apart
        keys = {s["comparability_key"] for s in proj["segments"]}
        self.assertEqual(keys, {"cmp_gA", "cmp_gB"})

    def test_series_scope_excludes_other_series(self):
        s3 = _seed(FakeS3())
        with mock.patch.dict(os.environ, {srp.BUCKET_ENV: "edenseek-scout"}, clear=False):
            proj = si.build_geometry_intelligence_scoped(level="series", issue_prefix=I1, client=s3)
        self.assertEqual(proj["scope"]["series_id"], "society_of_killers")
        self.assertEqual(proj["sample_sizes"]["reports"], 3)               # I1(2)+I2(1), NOT I3


class TestBenchmarkEndpoint(unittest.TestCase):
    def test_requires_auth(self):
        self.assertEqual(client.get("/benchmark/platform").status_code, 401)

    def test_bad_level_is_400(self):
        self.assertEqual(client.get("/benchmark/galaxy", auth=AUTH).status_code, 400)

    def test_non_platform_without_scope_is_400(self):
        self.assertEqual(client.get("/benchmark/series", auth=AUTH).status_code, 400)

    def test_malformed_scope_is_400(self):
        self.assertEqual(client.get("/benchmark/issue", params={"issue_prefix": "garbage"}, auth=AUTH).status_code, 400)

    def test_platform_serves_persisted(self):
        with mock.patch.object(scout_app.scout_benchmark, "load_projection", return_value={"task": "x"}) as m:
            resp = client.get("/benchmark/platform", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(m.call_args.args[0], "benchmark/platform.json")

    def test_series_scope_resolves_series_root_key(self):
        with mock.patch.object(scout_app.scout_benchmark, "load_projection", return_value={"task": "x"}) as m:
            resp = client.get("/benchmark/series", params={"issue_prefix": I1}, auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(m.call_args.args[0], f"{SOC_ROOT}/benchmark/benchmark.json")


class TestIntelligenceScopeParam(unittest.TestCase):
    def test_bad_scope_level_is_400(self):
        self.assertEqual(client.get("/intelligence/geometry", params={"level": "galaxy"}, auth=AUTH).status_code, 400)
        self.assertEqual(client.get("/intelligence/metadata", params={"level": "series"}, auth=AUTH).status_code, 400)  # no prefix

    def test_scoped_path_calls_scoped_loader(self):
        with mock.patch.object(scout_app.scout_intelligence, "build_geometry_intelligence_scoped",
                               return_value={"task": "geometry"}) as m:
            resp = client.get("/intelligence/geometry", params={"level": "platform"}, auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        m.assert_called_once_with(level="platform", issue_prefix="")

    def test_default_path_still_single_issue(self):
        # backward-compat: no level -> the single-issue loader (context=None for the env issue), unchanged.
        with mock.patch.object(scout_app.scout_intelligence, "build_geometry_intelligence",
                               return_value={"task": "geometry"}) as single, \
             mock.patch.object(scout_app.scout_intelligence, "build_geometry_intelligence_scoped") as scoped:
            resp = client.get("/intelligence/geometry", auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        single.assert_called_once()
        self.assertIsNone(single.call_args.kwargs.get("context"))   # env default
        scoped.assert_not_called()


if __name__ == "__main__":
    unittest.main()
