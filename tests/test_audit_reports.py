import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import audit_prioritization  # noqa: E402
import audit_failure_analysis  # noqa: E402
import audit_retrieval_blockers  # noqa: E402
import audit_history_analysis  # noqa: E402
import audit_reports  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"

REQUIRED_KEYS = {
    "dataset": {"dataset", "artifact_count", "quality_score", "findings"},
    "character": {"consistency_score", "characters", "reference_materials", "findings"},
    "dialogue": {"dialogue_completeness_score", "findings"},
    "retrieval": {"retrieval_readiness_score", "findings"},
    "weak_artifacts": {"total_flagged", "by_severity", "queue"},
    "review_priority": {"total", "by_impact", "queue"},
    "page_heatmap": {"pages", "unpaged_count"},
    "audit_history": {"history", "latest_delta"},
    "root_cause": {"artifact_count", "failures"},
    "highest_leverage": {"highest_leverage_failure", "ranked_failures", "process_backlog"},
    "failure_clusters": {"artifact_count", "issue_wide_failures", "page_clusters", "unpaged_cluster"},
    "retrieval_blockers": {"retrieval_readiness_score", "packet_coverage", "packet_blockers", "artifact_blockers"},
    "historical": {"dataset_id", "snapshots_analyzed", "confidence", "metrics", "failure_trends"},
}

_HIST_SNAPS = [
    {"timestamp": "t0", "dataset_id": "d", "quality_score": 50,
     "scores": {"metadata_completeness": 87, "character_consistency": 10,
                "dialogue_completeness": 70, "retrieval_readiness": 25},
     "artifact_count": 105, "weak_total_flagged": 105, "failure_summary": {"missing_characters": 95}},
    {"timestamp": "t1", "dataset_id": "d", "quality_score": 56,
     "scores": {"metadata_completeness": 87, "character_consistency": 20,
                "dialogue_completeness": 73, "retrieval_readiness": 25},
     "artifact_count": 105, "weak_total_flagged": 90, "failure_summary": {"missing_characters": 80}},
]

_SAMPLE_HISTORY = [{
    "timestamp": "2026-06-22T00:00:00Z", "dataset_id": "d", "quality_score": 53,
    "scores": {"metadata_completeness": 87, "character_consistency": 14,
               "dialogue_completeness": 73, "retrieval_readiness": 25},
    "artifact_count": 105, "weak_total_flagged": 105,
}]


def _extract_json_block(text):
    start = text.index("```json\n") + len("```json\n")
    end = text.index("\n```", start)
    return json.loads(text[start:end])


class TestAuditReports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))
        artifacts = cls.result["artifacts"]
        cls.result["blocks"]["review_priority"] = audit_prioritization.prioritize(artifacts)
        cls.result["blocks"]["page_heatmap"] = audit_prioritization.build_page_heatmap(artifacts)
        cls.result["blocks"]["audit_history"] = {"history": _SAMPLE_HISTORY, "latest_delta": None}
        rc = audit_failure_analysis.build_root_cause(artifacts)
        cls.result["blocks"]["root_cause"] = rc
        cls.result["blocks"]["highest_leverage"] = audit_failure_analysis.build_highest_leverage_failure(rc)
        cls.result["blocks"]["failure_clusters"] = audit_failure_analysis.build_failure_clusters(artifacts)
        cls.result["blocks"]["retrieval_blockers"] = audit_retrieval_blockers.build_retrieval_blockers(
            artifacts, cls.result["blocks"]["retrieval"])
        cls.result["blocks"]["historical"] = audit_history_analysis.build_historical_intelligence(_HIST_SNAPS)

    def test_write_all_reports(self):
        with tempfile.TemporaryDirectory() as d:
            written = audit_reports.write_reports(self.result, d, "2026-06-22T00:00:00Z")
            self.assertEqual(set(written), set(audit_reports.REPORT_FILES))
            for report_type, (subdir, filename) in audit_reports.REPORT_FILES.items():
                path = Path(d) / subdir / filename
                self.assertTrue(path.is_file(), report_type)

    def test_json_blocks_parse_and_have_required_keys(self):
        for report_type, block in self.result["blocks"].items():
            text = audit_reports.render_report(report_type, block, "2026-06-22T00:00:00Z")
            parsed = _extract_json_block(text)
            self.assertTrue(REQUIRED_KEYS[report_type].issubset(parsed.keys()), report_type)

    def test_render_is_deterministic(self):
        for report_type, block in self.result["blocks"].items():
            a = audit_reports.render_report(report_type, block, "2026-06-22T00:00:00Z")
            b = audit_reports.render_report(report_type, block, "2026-06-22T00:00:00Z")
            self.assertEqual(a, b, report_type)


if __name__ == "__main__":
    unittest.main()
