import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout  # noqa: E402

SAMPLE_SUMMARY = {
    "quality_score": 35,
    "artifact_count": 105,
    "scores": {
        "metadata_completeness": 100,
        "character_consistency": 0,
        "dialogue_completeness": 0,
        "retrieval_readiness": 25,
    },
    "weak_artifacts_summary": {
        "total_flagged": 105,
        "by_severity": {"critical": 0, "high": 104, "medium": 1, "low": 0},
    },
    "latest_reports": {"dataset": "reports/dataset/dataset_quality_report.md"},
    "last_audit": "2026-06-22T00:00:00Z",
}


class TestDatasetMemory(unittest.TestCase):
    def setUp(self):
        self._orig = scout.MEMORY_FILE
        self._tmp = tempfile.TemporaryDirectory()
        scout.MEMORY_FILE = Path(self._tmp.name) / "memory.json"

    def tearDown(self):
        scout.MEMORY_FILE = self._orig
        self._tmp.cleanup()

    def test_writes_only_dataset_track_and_preserves_existing(self):
        # Seed pre-existing memory with v0.3 fields.
        scout.save_memory({"report_count": 5, "last_report": "earlier", "themes": []})

        scout.update_dataset_memory(SAMPLE_SUMMARY)
        memory = scout.load_memory()

        # Existing top-level fields preserved.
        self.assertEqual(memory["report_count"], 5)
        self.assertEqual(memory["last_report"], "earlier")

        track = memory["projects"]["edenseek_dataset"]
        self.assertEqual(track["quality_score"], 35)
        self.assertEqual(track["audited_artifact_count"], 105)
        self.assertEqual(track["last_audit"], "2026-06-22T00:00:00Z")
        self.assertEqual(track["scores"], SAMPLE_SUMMARY["scores"])
        self.assertEqual(track["weak_artifacts"], SAMPLE_SUMMARY["weak_artifacts_summary"])
        self.assertEqual(track["latest_reports"], SAMPLE_SUMMARY["latest_reports"])
        # Other tracks not fabricated.
        self.assertEqual(set(memory["projects"].keys()), {"edenseek_dataset"})

    def test_idempotent(self):
        scout.update_dataset_memory(SAMPLE_SUMMARY)
        first = scout.load_memory()
        scout.update_dataset_memory(SAMPLE_SUMMARY)
        second = scout.load_memory()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
