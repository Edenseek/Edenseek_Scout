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


def _e(issue_id, *, series_id="society_of_killers", publisher_id="edenseek", tg="society_universe",
       state="edenseek_approved", audit_state="audited", revision="rev_x"):
    prefix = f"publishers/{publisher_id}/title_groups/{tg}/series/{series_id}/issues/{issue_id}"
    return reg.build_entry(
        issue_prefix=prefix,
        identity={"publisher_id": publisher_id, "title_group_id": tg,
                  "series_id": series_id, "issue_id": issue_id},
        published_revision_id=revision, review_id="rev_x", publication_state=state,
        audit={"audit_state": audit_state, "run_seq": 1, "run_id": "r", "report_id": "rep"})


class SeriesHealthTest(unittest.TestCase):
    def test_series_healthy_when_all_issues_healthy(self):
        proj = obs.series_health(reg.build_registry([_e("issue_001"), _e("issue_002")], generated_at="t1"))
        self.assertEqual(proj["projection"], "series_health")
        self.assertEqual(proj["registry_generated_at"], "t1")
        self.assertEqual(proj["summary"], {"healthy": 1, "attention": 0, "unknown": 0, "total": 1})
        rec = proj["records"][0]
        self.assertEqual(rec["health"], obs.HEALTHY)
        self.assertEqual(rec["series_id"], "society_of_killers")
        self.assertEqual(rec["issue_counts"], {"healthy": 2, "attention": 0, "unknown": 0, "total": 2})
        self.assertEqual(sorted(rec["issues"]), ["issue_001", "issue_002"])

    def test_series_attention_if_any_issue_attention(self):
        proj = obs.series_health(reg.build_registry(
            [_e("issue_001"), _e("issue_002", audit_state=reg.AUDIT_UNPROCESSED)]))
        rec = proj["records"][0]
        self.assertEqual(rec["health"], obs.ATTENTION)   # one pending issue -> series attention
        self.assertEqual(rec["issue_counts"], {"healthy": 1, "attention": 1, "unknown": 0, "total": 2})

    def test_series_unknown_propagates_without_attention(self):
        proj = obs.series_health(reg.build_registry([_e("issue_001"), _e("issue_002", revision=None)]))
        self.assertEqual(proj["records"][0]["health"], obs.UNKNOWN)   # healthy + unknown, no attention

    def test_multiple_series_each_rolled_up(self):
        proj = obs.series_health(reg.build_registry([
            _e("issue_001", series_id="s_a"),
            _e("issue_001", series_id="s_b", audit_state=reg.AUDIT_FAILED)]))
        by = {r["series_id"]: r["health"] for r in proj["records"]}
        self.assertEqual(by, {"s_a": obs.HEALTHY, "s_b": obs.ATTENTION})
        self.assertEqual(proj["summary"], {"healthy": 1, "attention": 1, "unknown": 0, "total": 2})


class PublisherHealthTest(unittest.TestCase):
    def test_publisher_aggregates_series(self):
        proj = obs.publisher_health(reg.build_registry([
            _e("issue_001", series_id="s_a"),
            _e("issue_001", series_id="s_b", audit_state=reg.AUDIT_UNPROCESSED)], generated_at="t1"))
        self.assertEqual(proj["projection"], "publisher_health")
        rec = proj["records"][0]
        self.assertEqual(rec["publisher_id"], "edenseek")
        self.assertEqual(rec["health"], obs.ATTENTION)   # one attention series -> publisher attention
        self.assertEqual(rec["series_counts"], {"healthy": 1, "attention": 1, "unknown": 0, "total": 2})
        self.assertEqual(rec["issue_counts"], {"healthy": 1, "attention": 1, "unknown": 0, "total": 2})
        self.assertEqual(sorted(rec["series"]), ["s_a", "s_b"])

    def test_multiple_publishers(self):
        proj = obs.publisher_health(reg.build_registry([
            _e("issue_001", publisher_id="edenseek"),
            _e("issue_001", publisher_id="acme", audit_state=reg.AUDIT_FAILED)]))
        by = {r["publisher_id"]: r["health"] for r in proj["records"]}
        self.assertEqual(by, {"acme": obs.ATTENTION, "edenseek": obs.HEALTHY})
        self.assertEqual(proj["summary"], {"healthy": 1, "attention": 1, "unknown": 0, "total": 2})

    def test_coherence_publisher_equals_rollup_over_all_issues(self):
        # associativity: publisher(series(issues)) == roll_up over the publisher's issue healths directly
        entries = [
            _e("issue_001", series_id="s_a"),                                  # healthy
            _e("issue_002", series_id="s_a", audit_state=reg.AUDIT_UNPROCESSED),  # attention
            _e("issue_001", series_id="s_b", revision=None),                   # unknown
        ]
        registry = reg.build_registry(entries)
        pub = obs.publisher_health(registry)["records"][0]["health"]
        issue_healths = [obs.assess_issue(e)[0] for e in entries]
        self.assertEqual(pub, obs.roll_up(issue_healths))
        self.assertEqual(pub, obs.ATTENTION)

    def test_tree_of_one_healthy_all_levels(self):
        registry = reg.build_registry([_e("issue_001")], generated_at="t1")
        self.assertEqual(obs.issue_health(registry)["records"][0]["health"], obs.HEALTHY)
        self.assertEqual(obs.series_health(registry)["records"][0]["health"], obs.HEALTHY)
        self.assertEqual(obs.publisher_health(registry)["records"][0]["health"], obs.HEALTHY)


if __name__ == "__main__":
    unittest.main()
