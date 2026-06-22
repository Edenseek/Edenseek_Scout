import hashlib
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestAuditScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))

    def test_artifact_count(self):
        self.assertEqual(self.result["artifact_count"], 105)

    def test_score_bounds(self):
        for k, v in self.result["scores"].items():
            self.assertGreaterEqual(v, 0, k)
            self.assertLessEqual(v, 100, k)

    def test_known_scores_regression(self):
        # Locked against the committed Society of Killers issue-1 fixture.
        self.assertEqual(self.result["scores"], {
            "metadata_completeness": 87,
            "character_consistency": 14,
            "dialogue_completeness": 73,
            "retrieval_readiness": 25,
        })
        self.assertEqual(self.result["quality_score"], 53)

    def test_coverage_cross_check(self):
        # Recompute presence coverage independently from the loaded data.
        outputs = audit_inputs.load_inputs(FIXTURE_DIR)["llm_outputs"]
        n = len(outputs)
        chars = sum(1 for o in outputs
                    if (o.get("output", {}).get("entities", {}) or {}).get("characters"))
        dlg = sum(1 for o in outputs
                  if (o.get("output", {}).get("narrative", {}) or {}).get("dialogue"))
        self.assertEqual(self.result["scores"]["character_consistency"], round(100 * chars / n))
        self.assertEqual(self.result["scores"]["dialogue_completeness"], round(100 * dlg / n))

    def test_retrieval_reflects_unready_packet(self):
        rb = self.result["blocks"]["retrieval"]
        self.assertEqual(rb["packets_evaluated"], 1)
        self.assertLess(rb["retrieval_readiness_score"], 100)
        gaps = " ".join(f["gap"] for f in rb["findings"])
        self.assertIn("confidence", gaps.lower())

    def test_weak_queue_all_flagged_and_sorted(self):
        weak = self.result["blocks"]["weak_artifacts"]
        self.assertEqual(weak["total_flagged"], 105)
        self.assertEqual(sum(weak["by_severity"].values()), 105)
        ranks = [audit_scoring.SEVERITY_RANK[q["severity"]] for q in weak["queue"]]
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_quality_score_matches_weighted_formula(self):
        s = self.result["scores"]
        expected = round(sum(s[k] * audit_scoring.WEIGHTS[k] for k in audit_scoring.WEIGHTS))
        self.assertEqual(self.result["quality_score"], expected)

    def test_determinism(self):
        again = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))
        self.assertEqual(self.result, again)

    def test_inputs_not_mutated(self):
        before = {p.name: _sha(p) for p in FIXTURE_DIR.iterdir() if p.is_file()}
        audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))
        after = {p.name: _sha(p) for p in FIXTURE_DIR.iterdir() if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
