"""Tests for scout_observability — Health Projections (D8 Increment 1).

Covers the atomic per-issue health rule (all states + reasons), the rollup primitive (for future
series/publisher projections), the summary counts, and the Issue Health projection envelope over a
synthetic Registry. Pure + deterministic; nothing here does I/O. Drift guards pin the mirrored
constants against their canonical sources.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_observability as obs  # noqa: E402
import scout_registry as reg  # noqa: E402
import review_contract_adapter as rca  # noqa: E402

IDENT = {"publisher_id": "edenseek", "title_group_id": "society_universe",
         "series_id": "society_of_killers", "issue_id": "issue_001"}
P1 = "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001"


def _entry(*, state="edenseek_approved", revision="rev_x", audit_state="audited"):
    return reg.build_entry(
        issue_prefix=P1, identity=IDENT, published_revision_id=revision, review_id="rev_x",
        publication_state=state,
        audit={"audit_state": audit_state, "run_seq": 3, "run_id": "run_x", "report_id": "rep3"})


class DriftGuardTest(unittest.TestCase):
    def test_constants_match_canonical_sources(self):
        self.assertEqual(obs.STATE_EDENSEEK_APPROVED, rca.STATE_EDENSEEK_APPROVED)
        self.assertEqual(obs.AUDIT_AUDITED, reg.AUDIT_AUDITED)
        self.assertEqual(obs.AUDIT_FAILED, reg.AUDIT_FAILED)


class AssessIssueTest(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(obs.assess_issue(_entry()), (obs.HEALTHY, []))

    def test_attention_audit_pending(self):
        h, r = obs.assess_issue(_entry(audit_state=reg.AUDIT_UNPROCESSED))
        self.assertEqual(h, obs.ATTENTION)
        self.assertEqual(r, [obs.REASON_AUDIT_PENDING])

    def test_attention_audit_failed(self):
        h, r = obs.assess_issue(_entry(audit_state=reg.AUDIT_FAILED))
        self.assertEqual((h, r), (obs.ATTENTION, [obs.REASON_AUDIT_FAILED]))

    def test_attention_not_platform_approved(self):
        h, r = obs.assess_issue(_entry(state=reg.STATE_CREATOR_APPROVED))
        self.assertEqual(h, obs.ATTENTION)
        self.assertEqual(r, [obs.REASON_NOT_PLATFORM_APPROVED])

    def test_attention_multiple_reasons(self):
        h, r = obs.assess_issue(_entry(state=reg.STATE_CREATOR_APPROVED, audit_state=reg.AUDIT_FAILED))
        self.assertEqual(h, obs.ATTENTION)
        self.assertEqual(r, [obs.REASON_NOT_PLATFORM_APPROVED, obs.REASON_AUDIT_FAILED])

    def test_unknown_when_no_revision(self):
        h, r = obs.assess_issue(reg.build_entry(issue_prefix=P1, identity=IDENT))  # unpublished
        self.assertEqual((h, r), (obs.UNKNOWN, [obs.REASON_NO_PUBLISHED_REVISION]))


class RollUpTest(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(obs.roll_up([]), obs.UNKNOWN)
        self.assertEqual(obs.roll_up([obs.HEALTHY, obs.HEALTHY]), obs.HEALTHY)
        self.assertEqual(obs.roll_up([obs.HEALTHY, obs.ATTENTION]), obs.ATTENTION)   # problems surface
        self.assertEqual(obs.roll_up([obs.ATTENTION, obs.UNKNOWN]), obs.ATTENTION)
        self.assertEqual(obs.roll_up([obs.HEALTHY, obs.UNKNOWN]), obs.UNKNOWN)       # incomplete -> unknown
        self.assertEqual(obs.roll_up([obs.UNKNOWN]), obs.UNKNOWN)


class IssueHealthProjectionTest(unittest.TestCase):
    def _registry(self, entries):
        return reg.build_registry(entries, generated_at="2026-07-30T18:31:24.804Z")

    def test_projection_envelope_and_summary(self):
        p2 = P1.replace("issue_001", "issue_002")
        entries = [
            _entry(),  # healthy
            reg.build_entry(issue_prefix=p2, identity={**IDENT, "issue_id": "issue_002"},
                            published_revision_id="rev_y", publication_state="edenseek_approved",
                            audit={"audit_state": reg.AUDIT_UNPROCESSED, "run_seq": None,
                                   "run_id": None, "report_id": None}),  # attention
        ]
        proj = obs.issue_health(self._registry(entries))
        self.assertEqual(proj["projection"], "issue_health")
        self.assertEqual(proj["health_version"], obs.HEALTH_VERSION)
        self.assertEqual(proj["registry_generated_at"], "2026-07-30T18:31:24.804Z")
        self.assertEqual(proj["summary"], {"healthy": 1, "attention": 1, "unknown": 0, "total": 2})
        # records sorted by issue prefix; each carries identity + health + reasons
        self.assertEqual([r["issue_id"] for r in proj["records"]], ["issue_001", "issue_002"])
        self.assertEqual(proj["records"][0]["health"], obs.HEALTHY)
        self.assertEqual(proj["records"][1]["health"], obs.ATTENTION)
        self.assertEqual(proj["records"][1]["reasons"], [obs.REASON_AUDIT_PENDING])

    def test_empty_registry(self):
        proj = obs.issue_health(reg.build_registry([]))
        self.assertEqual(proj["summary"], {"healthy": 0, "attention": 0, "unknown": 0, "total": 0})
        self.assertEqual(proj["records"], [])

    def test_certified_tree_of_one_is_healthy(self):
        # mirrors the live production Registry: edenseek_approved + audited -> healthy
        proj = obs.issue_health(self._registry([_entry()]))
        self.assertEqual(proj["summary"], {"healthy": 1, "attention": 0, "unknown": 0, "total": 1})
        self.assertEqual(proj["records"][0]["health"], obs.HEALTHY)


if __name__ == "__main__":
    unittest.main()
