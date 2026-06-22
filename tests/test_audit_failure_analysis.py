import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import audit_failure_analysis as fa  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"

KNOWN_FAILURE_TYPES = {d["failure_type"] for d in fa.FAILURE_DEFS}


class TestRootCause(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))["artifacts"]
        cls.rc = fa.build_root_cause(cls.artifacts)

    def test_deterministic(self):
        self.assertEqual(fa.build_root_cause(self.artifacts), self.rc)

    def test_artifact_count(self):
        self.assertEqual(self.rc["artifact_count"], 105)

    def test_only_known_failure_types(self):
        for f in self.rc["failures"]:
            self.assertIn(f["failure_type"], KNOWN_FAILURE_TYPES)

    def test_counts_match_predicates(self):
        defs = {d["failure_type"]: d for d in fa.FAILURE_DEFS}
        for f in self.rc["failures"]:
            expected = sum(1 for a in self.artifacts if defs[f["failure_type"]]["predicate"](a))
            self.assertEqual(f["affected_count"], expected, f["failure_type"])
            self.assertEqual(f["affected_percent"], round(100 * expected / 105))

    def test_reconciles_with_phase1(self):
        counts = {f["failure_type"]: f["affected_count"] for f in self.rc["failures"]}
        # 15/105 have characters, 77/105 have dialogue, 1/105 approved, 0/105 reviewed.
        self.assertEqual(counts["missing_characters"], 90)
        self.assertEqual(counts["missing_dialogue"], 28)
        self.assertEqual(counts["not_approved"], 104)
        self.assertEqual(counts["unreviewed"], 105)

    def test_sorted_by_prevalence(self):
        counts = [f["affected_count"] for f in self.rc["failures"]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_no_numeric_prediction(self):
        for f in self.rc["failures"]:
            self.assertNotIn("expected_score_increase", f)
            self.assertIn(f["estimated_impact"], {"high", "medium", "low"})


class TestHighestLeverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifacts = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))["artifacts"]
        cls.rc = fa.build_root_cause(artifacts)
        cls.hl = fa.build_highest_leverage_failure(cls.rc)

    def test_top_is_content_domain(self):
        top = self.hl["highest_leverage_failure"]
        self.assertIsNotNone(top)
        self.assertIn(top["domain"], fa.CONTENT_DOMAINS)

    def test_top_is_largest_content_failure(self):
        # missing_characters (90) is the largest content-quality failure here.
        self.assertEqual(self.hl["highest_leverage_failure"]["failure_type"], "missing_characters")
        self.assertEqual(self.hl["highest_leverage_failure"]["estimated_impact"], "high")

    def test_process_backlog_separate(self):
        self.assertIn("not_approved", self.hl["process_backlog"])
        self.assertIn("unreviewed", self.hl["process_backlog"])
        # workflow failures must not appear in ranked content failures
        ranked_types = {f["failure_type"] for f in self.hl["ranked_failures"]}
        self.assertNotIn("not_approved", ranked_types)

    def test_is_diagnostic_not_prescriptive(self):
        top = self.hl["highest_leverage_failure"]
        for forbidden in ("engineering_target", "suggested_action", "recommended_action",
                          "expected_score_increase"):
            self.assertNotIn(forbidden, top)

    def test_deterministic(self):
        self.assertEqual(fa.build_highest_leverage_failure(self.rc), self.hl)


if __name__ == "__main__":
    unittest.main()
