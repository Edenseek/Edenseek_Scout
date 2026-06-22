import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import audit_prioritization  # noqa: E402
import audit_failure_analysis  # noqa: E402
import audit_retrieval_blockers  # noqa: E402
import audit_retrieval_readiness  # noqa: E402
import audit_history_analysis  # noqa: E402
import audit_digest  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"


def _build_blocks():
    result = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))
    a = result["artifacts"]
    result["blocks"]["review_priority"] = audit_prioritization.prioritize(a)
    rc = audit_failure_analysis.build_root_cause(a)
    result["blocks"]["root_cause"] = rc
    result["blocks"]["highest_leverage"] = audit_failure_analysis.build_highest_leverage_failure(rc)
    result["blocks"]["retrieval_blockers"] = audit_retrieval_blockers.build_retrieval_blockers(
        a, result["blocks"]["retrieval"])
    result["blocks"]["historical"] = audit_history_analysis.build_historical_intelligence([])
    result["blocks"]["retrieval_readiness"] = audit_retrieval_readiness.build_retrieval_readiness(
        result["blocks"]["retrieval"], result["blocks"]["retrieval_blockers"], None, "d")
    return result["blocks"]


class TestDigest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocks = _build_blocks()
        cls.digest = audit_digest.build_digest(cls.blocks)

    def test_deterministic(self):
        self.assertEqual(audit_digest.build_digest(self.blocks), self.digest)

    def test_projects_from_blocks_no_new_values(self):
        d = self.digest
        self.assertEqual(d["quality_score"], self.blocks["dataset"]["quality_score"])
        self.assertEqual(d["readiness"]["verdict"], self.blocks["retrieval_readiness"]["verdict"])
        self.assertEqual(d["review"]["total"], self.blocks["review_priority"]["total"])
        self.assertEqual(d["highest_leverage_failure"],
                         self.blocks["highest_leverage"]["highest_leverage_failure"])

    def test_top_items_capped(self):
        self.assertLessEqual(len(self.digest["review"]["top_items"]), audit_digest.TOP_REVIEW_ITEMS)
        # Top item equals priority rank 1 from the source queue.
        if self.digest["review"]["top_items"]:
            self.assertEqual(self.digest["review"]["top_items"][0]["priority_rank"], 1)

    def test_insufficient_history_handles_gracefully(self):
        # historical here is insufficient_history -> no delta.
        self.assertIsNone(self.digest["quality_delta"])
        self.assertIsNone(self.digest["changes_since_last_audit"])
        self.assertEqual(self.digest["trend"]["confidence"], "insufficient_history")

    def test_report_links_present(self):
        self.assertIn("review_priority", self.digest["report_links"])
        self.assertIn("retrieval_readiness", self.digest["report_links"])

    def test_no_recommendation_or_prediction(self):
        import json
        blob = json.dumps({k: v for k, v in self.digest.items() if k != "note"})
        for forbidden in ("recommendation", "predicted", "expected_score_increase", "suggested_action"):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
