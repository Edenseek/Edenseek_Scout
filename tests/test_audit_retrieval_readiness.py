import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_retrieval_readiness as rr  # noqa: E402


def _retrieval_block(packets, confidence_unscored=0, untraceable=0, score=50):
    findings = []
    for i in range(confidence_unscored):
        findings.append({"packet_id": f"packet_{i}", "gap": "Evidence confidence not scored (null).",
                         "severity": "high"})
    for i in range(untraceable):
        findings.append({"packet_id": f"packet_{i}", "gap": "No matched_fields recorded.",
                         "severity": "high"})
    return {"retrieval_readiness_score": score, "packets_evaluated": packets,
            "artifacts_referenced": 0, "findings": findings}


def _blockers(coverage_percent=90, no_grounding_percent=None):
    artifact_blockers = []
    if no_grounding_percent is not None:
        artifact_blockers.append({"blocker_type": "no_grounding", "severity": "high",
                                  "affected_count": 0, "affected_percent": no_grounding_percent,
                                  "estimated_impact": "low"})
    packet_blockers = []
    if coverage_percent < 100:
        packet_blockers.append({"blocker": "low_packet_coverage", "severity": "high", "affected_packets": 1})
    return {"retrieval_readiness_score": 50,
            "packet_coverage": {"packets_evaluated": 5, "artifacts_referenced": 4,
                                "artifact_count": 5, "coverage_percent": coverage_percent},
            "packet_blockers": packet_blockers, "artifact_blockers": artifact_blockers}


def _status_of(result, dim):
    return next(d["status"] for d in result["dimensions"] if d["dimension"] == dim)


class TestRetrievalReadiness(unittest.TestCase):
    def test_all_strong_is_ready(self):
        r = rr.build_retrieval_readiness(_retrieval_block(5, 0, 0), _blockers(90, 0))
        self.assertEqual(r["verdict"], "ready")
        self.assertEqual(_status_of(r, "grounding_quality"), "strong")
        self.assertEqual(r["weaknesses"], [])

    def test_grounding_weak_is_hard_stop(self):
        # grounding 1/5 = 20% weak; everything else strong.
        r = rr.build_retrieval_readiness(_retrieval_block(5, 4, 0), _blockers(90, 0))
        self.assertEqual(_status_of(r, "grounding_quality"), "weak")
        self.assertEqual(r["verdict"], "not_ready")

    def test_weak_non_grounding_is_partially_ready(self):
        # grounding strong (no unscored); coverage 30% weak.
        r = rr.build_retrieval_readiness(_retrieval_block(5, 0, 0), _blockers(30, 0))
        self.assertEqual(_status_of(r, "grounding_quality"), "strong")
        self.assertEqual(_status_of(r, "coverage"), "weak")
        self.assertEqual(r["verdict"], "partially_ready")

    def test_grounding_adequate_with_weak_is_partially(self):
        # grounding 3/5 = 60% adequate (not weak); coverage weak.
        r = rr.build_retrieval_readiness(_retrieval_block(5, 2, 0), _blockers(10, 0))
        self.assertEqual(_status_of(r, "grounding_quality"), "adequate")
        self.assertEqual(r["verdict"], "partially_ready")

    def test_status_bands(self):
        self.assertEqual(rr._status(80), "strong")
        self.assertEqual(rr._status(79), "adequate")
        self.assertEqual(rr._status(40), "adequate")
        self.assertEqual(rr._status(39), "weak")

    def test_coverage_reconciles_with_blockers(self):
        blk = _blockers(73, 0)
        r = rr.build_retrieval_readiness(_retrieval_block(5, 0, 0), blk)
        cov = next(d for d in r["dimensions"] if d["dimension"] == "coverage")
        self.assertEqual(cov["measured_percent"], blk["packet_coverage"]["coverage_percent"])

    def test_trend_passthrough(self):
        trend = {"retrieval_readiness": "improving", "confidence": "trend"}
        r = rr.build_retrieval_readiness(_retrieval_block(5, 0, 0), _blockers(90, 0), trend)
        self.assertEqual(r["trend"], trend)

    def test_no_recommendation_or_prediction(self):
        import json
        r = rr.build_retrieval_readiness(_retrieval_block(5, 4, 0), _blockers(10, 50))
        # Scan the data, not the standing disclaimer note.
        blob = json.dumps({k: v for k, v in r.items() if k != "note"})
        for forbidden in ("recommendation", "predicted", "expected_score_increase", "suggested_action"):
            self.assertNotIn(forbidden, blob)

    def test_deterministic(self):
        a = rr.build_retrieval_readiness(_retrieval_block(5, 1, 2), _blockers(50, 9))
        b = rr.build_retrieval_readiness(_retrieval_block(5, 1, 2), _blockers(50, 9))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
