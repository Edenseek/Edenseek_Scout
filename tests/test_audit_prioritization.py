import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import audit_prioritization as ap  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"
_SENTINEL = 10 ** 9


def _order_key(entry):
    page = entry["page"]
    return (
        -audit_scoring.SEVERITY_RANK[entry["severity"]],
        _SENTINEL if not isinstance(page, int) else page,
        entry["effort"],
        str(entry["artifact_id"]),
    )


class TestPrioritization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))["artifacts"]
        cls.prio = ap.prioritize(cls.artifacts)

    def test_includes_all_weak(self):
        weak = sum(1 for a in self.artifacts if a["weak"])
        self.assertEqual(self.prio["total"], weak)
        self.assertEqual(sum(self.prio["by_impact"].values()), weak)

    def test_known_by_impact_regression(self):
        self.assertEqual(self.prio["by_impact"], {"high": 104, "medium": 1, "low": 0})

    def test_rank_one_is_lowest_page_high_severity(self):
        top = self.prio["queue"][0]
        self.assertEqual(top["priority_rank"], 1)
        self.assertEqual(top["severity"], "high")
        self.assertEqual(top["estimated_impact"], "high")
        self.assertEqual(top["page"], 2)

    def test_impact_band_mapping(self):
        for e in self.prio["queue"]:
            self.assertEqual(e["estimated_impact"], ap.IMPACT_BY_SEVERITY[e["severity"]])
            self.assertIn(e["estimated_impact"], {"high", "medium", "low"})

    def test_ordering_is_total_and_correct(self):
        keys = [_order_key(e) for e in self.prio["queue"]]
        self.assertEqual(keys, sorted(keys))
        ranks = [e["priority_rank"] for e in self.prio["queue"]]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_order_independent_and_deterministic(self):
        again = ap.prioritize(list(reversed(self.artifacts)))
        self.assertEqual(again, self.prio)

    def test_no_numeric_score_impact(self):
        for e in self.prio["queue"]:
            self.assertNotIn("expected_score_increase", e)
            self.assertNotIn("expected_score_impact", e)


class TestPageHeatmap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))["artifacts"]
        cls.heat = ap.build_page_heatmap(cls.artifacts)

    def test_counts_sum_to_total(self):
        total = sum(p["artifact_count"] for p in self.heat["pages"])
        self.assertEqual(total, len(self.artifacts))

    def test_unpaged_bucket_regression(self):
        self.assertEqual(self.heat["unpaged_count"], 9)
        paged = [p for p in self.heat["pages"] if isinstance(p["page"], int)]
        self.assertEqual(len(paged), 29)

    def test_sorted_worst_first(self):
        rank = {"high": 3, "medium": 2, "low": 1}
        keys = [(-rank[p["page_impact"]], -p["weak_count"],
                 _SENTINEL if not isinstance(p["page"], int) else p["page"])
                for p in self.heat["pages"]]
        self.assertEqual(keys, sorted(keys))

    def test_deterministic(self):
        self.assertEqual(ap.build_page_heatmap(self.artifacts), self.heat)


if __name__ == "__main__":
    unittest.main()
