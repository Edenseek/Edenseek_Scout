import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import audit_retrieval_blockers as rb  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"

KNOWN_BLOCKERS = {b[0] for b in rb._ARTIFACT_BLOCKERS}


class TestRetrievalBlockers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))
        cls.artifacts = result["artifacts"]
        cls.retrieval_block = result["blocks"]["retrieval"]
        cls.blockers = rb.build_retrieval_blockers(cls.artifacts, cls.retrieval_block)

    def test_deterministic(self):
        self.assertEqual(rb.build_retrieval_blockers(self.artifacts, self.retrieval_block), self.blockers)

    def test_packet_coverage(self):
        pc = self.blockers["packet_coverage"]
        self.assertEqual(pc["artifact_count"], 105)
        # Only one packet referencing a single artifact in this fixture.
        self.assertEqual(pc["packets_evaluated"], 1)
        self.assertEqual(pc["artifacts_referenced"], 1)
        self.assertEqual(pc["coverage_percent"], round(100 * 1 / 105))

    def test_low_coverage_blocker_present(self):
        blockers = {b["blocker"] for b in self.blockers["packet_blockers"]}
        self.assertIn("low_packet_coverage", blockers)

    def test_artifact_blocker_counts_match(self):
        counts = {b["blocker_type"]: b["affected_count"] for b in self.blockers["artifact_blockers"]}
        self.assertEqual(counts.get("missing_characters"), 90)
        self.assertEqual(counts.get("missing_dialogue"), 28)
        self.assertEqual(counts.get("missing_page_linkage"), 9)

    def test_only_known_blocker_types(self):
        for b in self.blockers["artifact_blockers"]:
            self.assertIn(b["blocker_type"], KNOWN_BLOCKERS)

    def test_thin_description_threshold(self):
        # Cross-check thin_description against the summary_length signal.
        expected = sum(1 for a in self.artifacts if 0 < a["summary_length"] < rb.THIN_DESCRIPTION_CHARS)
        counts = {b["blocker_type"]: b["affected_count"] for b in self.blockers["artifact_blockers"]}
        self.assertEqual(counts.get("thin_description", 0), expected)

    def test_no_numeric_prediction(self):
        for b in self.blockers["artifact_blockers"]:
            self.assertNotIn("expected_score_increase", b)
            self.assertIn(b["estimated_impact"], {"high", "medium", "low"})


if __name__ == "__main__":
    unittest.main()
