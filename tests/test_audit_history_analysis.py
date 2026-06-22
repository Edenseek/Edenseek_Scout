import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_history_analysis as ha  # noqa: E402


def _snap(ts, dataset="d", quality=50, meta=100, char=14, dlg=73, retr=25,
          n=105, weak=105, failures=None):
    return {
        "timestamp": ts, "dataset_id": dataset, "quality_score": quality,
        "scores": {"metadata_completeness": meta, "character_consistency": char,
                   "dialogue_completeness": dlg, "retrieval_readiness": retr},
        "artifact_count": n, "weak_total_flagged": weak,
        "failure_summary": failures or {},
    }


class TestHistoricalIntelligence(unittest.TestCase):
    def test_insufficient_history(self):
        r = ha.build_historical_intelligence([_snap("t0")])
        self.assertEqual(r["confidence"], "insufficient_history")
        self.assertEqual(r["metrics"], [])

    def test_confidence_levels(self):
        self.assertEqual(ha.build_historical_intelligence([])["confidence"], "insufficient_history")
        two = [_snap("t0"), _snap("t1")]
        self.assertEqual(ha.build_historical_intelligence(two)["confidence"], "preliminary")
        three = two + [_snap("t2")]
        self.assertEqual(ha.build_historical_intelligence(three)["confidence"], "trend")

    def test_metric_direction_polarity(self):
        snaps = [_snap("t0", quality=50, char=10, weak=100),
                 _snap("t1", quality=56, char=20, weak=80)]
        r = ha.build_historical_intelligence(snaps)
        m = {x["name"]: x for x in r["metrics"]}
        self.assertEqual(m["quality_score"]["direction"], "improving")   # higher better, +6
        self.assertEqual(m["character_consistency"]["direction"], "improving")
        self.assertEqual(m["weak_percent"]["direction"], "improving")    # lower better, fell

    def test_stable_within_epsilon(self):
        snaps = [_snap("t0", quality=53), _snap("t1", quality=54)]  # +1 <= epsilon
        r = ha.build_historical_intelligence(snaps)
        m = {x["name"]: x for x in r["metrics"]}
        self.assertEqual(m["quality_score"]["direction"], "stable")

    def test_failure_trend_and_new_resolved(self):
        snaps = [_snap("t0", failures={"missing_characters": 90, "unpaged": 9}),
                 _snap("t1", failures={"missing_characters": 60, "missing_dialogue": 30})]
        r = ha.build_historical_intelligence(snaps)
        ft = {f["failure_type"]: f for f in r["failure_trends"]}
        # missing_characters 86%->57% -> shrinking (improving)
        self.assertEqual(ft["missing_characters"]["direction"], "improving")
        self.assertIn("missing_dialogue", r["new_failures"])
        self.assertIn("unpaged", r["resolved_failures"])

    def test_most_recent_dataset_only(self):
        snaps = [_snap("t0", dataset="A", quality=10),
                 _snap("t1", dataset="B", quality=50),
                 _snap("t2", dataset="B", quality=60)]
        r = ha.build_historical_intelligence(snaps)
        self.assertEqual(r["dataset_id"], "B")
        self.assertEqual(r["snapshots_analyzed"], 2)
        m = {x["name"]: x for x in r["metrics"]}
        self.assertEqual(m["quality_score"]["first"], 50)  # ignores dataset A

    def test_explicit_dataset_id(self):
        snaps = [_snap("t0", dataset="A", quality=10), _snap("t1", dataset="A", quality=11),
                 _snap("t2", dataset="B", quality=99)]
        r = ha.build_historical_intelligence(snaps, dataset_id="A")
        self.assertEqual(r["dataset_id"], "A")
        self.assertEqual(r["snapshots_analyzed"], 2)

    def test_observed_correlation_is_observational(self):
        snaps = [_snap("t0", quality=50, failures={"unreviewed": 105, "missing_characters": 90}),
                 _snap("t1", quality=55, failures={"unreviewed": 80, "missing_characters": 70})]
        r = ha.build_historical_intelligence(snaps)
        self.assertTrue(r["observed_correlations"])
        c = r["observed_correlations"][0]
        self.assertEqual(c["inferred_changes"]["reviews_performed"], 25)
        self.assertEqual(c["inferred_changes"]["characters_added"], 20)
        self.assertEqual(c["quality_change"], 5)
        # No prediction / recommendation anywhere.
        for forbidden in ("recommendation", "predicted", "expected_score_increase", "suggested_action"):
            self.assertNotIn(forbidden, c)

    def test_deterministic(self):
        snaps = [_snap("t0", quality=50, failures={"missing_characters": 90}),
                 _snap("t1", quality=55, failures={"missing_characters": 70}),
                 _snap("t2", quality=58, failures={"missing_characters": 60})]
        self.assertEqual(ha.build_historical_intelligence(snaps),
                         ha.build_historical_intelligence(snaps))


if __name__ == "__main__":
    unittest.main()
