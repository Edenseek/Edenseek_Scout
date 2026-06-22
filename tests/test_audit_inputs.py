import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"


class TestAuditInputs(unittest.TestCase):
    def test_load_counts(self):
        data = audit_inputs.load_inputs(FIXTURE_DIR)
        self.assertEqual(len(data["approved_artifacts"]), 1)
        self.assertEqual(len(data["llm_outputs"]), 105)
        self.assertEqual(len(data["packets"]), 1)
        self.assertTrue(data["dataset_id"].endswith("issue_1"))

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(audit_inputs.AuditInputError):
                audit_inputs.load_inputs(d)

    def test_contract_violation_raises(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / audit_inputs.DATASET_FILE).write_text(json.dumps({"wrong_key": []}))
            (d / audit_inputs.LLM_OUTPUTS_FILE).write_text(json.dumps({"llm_enrichment_outputs": []}))
            (d / audit_inputs.PACKETS_FILE).write_text(json.dumps({"retrieval_evidence_packets": []}))
            with self.assertRaises(audit_inputs.AuditInputError):
                audit_inputs.load_inputs(d)


if __name__ == "__main__":
    unittest.main()
