import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import audit_reports  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"

REQUIRED_KEYS = {
    "dataset": {"dataset", "artifact_count", "quality_score", "findings"},
    "character": {"consistency_score", "characters", "reference_materials", "findings"},
    "dialogue": {"dialogue_completeness_score", "findings"},
    "retrieval": {"retrieval_readiness_score", "findings"},
    "weak_artifacts": {"total_flagged", "by_severity", "queue"},
}


def _extract_json_block(text):
    start = text.index("```json\n") + len("```json\n")
    end = text.index("\n```", start)
    return json.loads(text[start:end])


class TestAuditReports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))

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
