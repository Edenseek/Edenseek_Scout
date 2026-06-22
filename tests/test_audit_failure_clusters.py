import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import audit_failure_analysis as fa  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"


class TestFailureClusters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))["artifacts"]
        cls.clusters = fa.build_failure_clusters(cls.artifacts)

    def test_deterministic(self):
        self.assertEqual(fa.build_failure_clusters(self.artifacts), self.clusters)

    def test_issue_wide_at_threshold(self):
        types = {f["failure_type"] for f in self.clusters["issue_wide_failures"]}
        # >= 80% coverage: missing_characters (86%), unreviewed/not_locked (100%), not_approved (99%).
        self.assertIn("missing_characters", types)
        self.assertIn("unreviewed", types)
        self.assertIn("not_approved", types)
        for f in self.clusters["issue_wide_failures"]:
            self.assertGreaterEqual(f["affected_percent"], fa.ISSUE_WIDE_THRESHOLD_PCT)

    def test_workflow_visible_and_tagged(self):
        workflow = [f for f in self.clusters["issue_wide_failures"] if f["category"] == "workflow"]
        self.assertTrue(workflow)  # not hidden
        for f in workflow:
            self.assertEqual(f["domain"], "approval_workflow")

    def test_content_and_workflow_separated_by_category(self):
        for f in self.clusters["issue_wide_failures"]:
            self.assertIn(f["category"], {"content", "workflow"})
            expected = "workflow" if f["domain"] == "approval_workflow" else "content"
            self.assertEqual(f["category"], expected)

    def test_page_clusters_respect_thresholds(self):
        for c in self.clusters["page_clusters"]:
            self.assertGreaterEqual(c["affected_count"], fa.PAGE_CLUSTER_MIN_COUNT)
            self.assertGreaterEqual(c["concentration_percent"], fa.PAGE_CLUSTER_MIN_FRACTION * 100)

    def test_unpaged_cluster(self):
        uc = self.clusters["unpaged_cluster"]
        self.assertIsNotNone(uc)
        self.assertEqual(uc["artifact_count"], 9)
        # 'unpaged' failure affects all 9 unpaged artifacts.
        unpaged_counts = {f["failure_type"]: f["affected_count"] for f in uc["failures"]}
        self.assertEqual(unpaged_counts.get("unpaged"), 9)

    def test_no_numeric_prediction(self):
        for f in self.clusters["issue_wide_failures"]:
            self.assertNotIn("expected_score_increase", f)
            self.assertIn(f["estimated_impact"], {"high", "medium", "low"})


if __name__ == "__main__":
    unittest.main()
