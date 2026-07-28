"""Orchestrator + Correction Ledger + determinism tests (Scout 6.3, Phase A)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import _delta_fixtures as fx  # noqa: E402
from delta_auditor import run_delta_audit, serialize_delta_report  # noqa: E402


class TestDeltaAuditor(unittest.TestCase):
    def test_end_to_end_generated(self):
        rep = run_delta_audit(fx.review_generated(), fx.platform_approval())
        self.assertEqual(rep["applicability"], "generated_publication")
        self.assertTrue(rep["geometry_delta"]["applicable"])
        self.assertTrue(rep["metadata_delta"]["applicable"])
        self.assertEqual(rep["provenance"]["generated_snapshot_revision_id"], "rev_gen0000")

    def test_publisher_state_kept_separate(self):
        rep = run_delta_audit(fx.review_generated(), fx.platform_approval())
        self.assertEqual(rep["publisher_certified_state"]["canonical_dataset_state"], "edenseek_approved")
        self.assertIsNotNone(rep["publisher_certified_state"]["platform_readiness"])
        self.assertNotIn("canonical_dataset_state", rep["geometry_delta"])
        self.assertNotIn("canonical_dataset_state", rep["metadata_delta"])

    def test_ledger_cites_missing_spread_and_metadata(self):
        rep = run_delta_audit(fx.review_generated(), fx.platform_approval())
        ops = {(e["artifact_id"], e["stage"], e["operation"]) for e in rep["correction_ledger"]}
        self.assertIn(("11::NEW::1", "geometry", "missing_panel"), ops)
        self.assertIn(("spread_12_13::p1", "geometry", "spread_missing_panel"), ops)
        # panel_3 carries field corrections (tags edited + chars/summary edited);
        # panel_7 is a clean accept (null tags, chars/summary accepted) -> NOT a correction
        self.assertIn(("society_of_killers_1_3::p1", "metadata", "fields_corrected"), ops)
        self.assertNotIn(("society_of_killers_1_7::p1", "metadata", "fields_corrected"), ops)

    def test_manual_produces_no_delta(self):
        rep = run_delta_audit(fx.review_manual())
        self.assertEqual(rep["applicability"], "manual")
        self.assertFalse(rep["geometry_delta"]["applicable"])
        self.assertFalse(rep["metadata_delta"]["applicable"])
        self.assertEqual(rep["correction_ledger"], [])
        self.assertEqual(rep["publisher_certified_state"]["canonical_dataset_state"], "creator_approved")

    def test_deterministic_byte_identical(self):
        a = serialize_delta_report(run_delta_audit(fx.review_generated(), fx.platform_approval()))
        b = serialize_delta_report(run_delta_audit(fx.review_generated(), fx.platform_approval()))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
