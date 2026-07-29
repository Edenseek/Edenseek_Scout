"""Tests for scout_context.IssueContext (Phase 1 — behavior-neutral).

The central guarantee is **byte-equivalence**: ``IssueContext.from_env()`` must reproduce the
exact bucket / prefix / region / identity the existing modules derive from the same environment.
These tests compare the context against the modules' own derivations (``audit_s3_source`` for the
approved read surface, ``scout_report_publisher`` for the Scout write surface), plus the normal
fail-loud and immutability behavior. Nothing in production consumes IssueContext yet.
"""
import dataclasses
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_context as sc  # noqa: E402
import audit_s3_source as a3  # noqa: E402
import scout_report_publisher as srp  # noqa: E402

# Prod-like ownership chain (matches test_scout_report_index REPO_PREFIX + IDENT).
SCOUT_PREFIX = "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001"
APPROVED_PREFIX = SCOUT_PREFIX + "/approved"
IDENT = {"publisher_id": "edenseek", "title_group_id": "society_universe",
         "series_id": "society_of_killers", "issue_id": "issue_001"}


def _env(**over):
    e = {
        sc.APPROVED_BUCKET_ENV: "edenseek-publishing",
        sc.APPROVED_PREFIX_ENV: APPROVED_PREFIX,
        sc.APPROVED_REGION_ENV: "us-west-2",
        sc.SCOUT_BUCKET_ENV: "edenseek-scout",
        sc.SCOUT_PREFIX_ENV: SCOUT_PREFIX,
        sc.SCOUT_REGION_ENV: "us-west-2",
    }
    e.update(over)
    return e


class EnvContractTest(unittest.TestCase):
    """The env-var names + defaults must not drift from the modules they mirror."""

    def test_env_names_match_modules(self):
        self.assertEqual(sc.APPROVED_BUCKET_ENV, a3.BUCKET_ENV)
        self.assertEqual(sc.APPROVED_PREFIX_ENV, a3.PREFIX_ENV)
        self.assertEqual(sc.APPROVED_REGION_ENV, a3.REGION_ENV)
        self.assertEqual(sc.SCOUT_BUCKET_ENV, srp.BUCKET_ENV)
        self.assertEqual(sc.SCOUT_PREFIX_ENV, srp.PREFIX_ENV)
        self.assertEqual(sc.SCOUT_REGION_ENV, srp.REGION_ENV)

    def test_default_region_matches_modules(self):
        self.assertEqual(sc.DEFAULT_REGION, a3.DEFAULT_REGION)
        self.assertEqual(sc.DEFAULT_REGION, srp.DEFAULT_REGION)


class ByteEquivalenceTest(unittest.TestCase):
    """from_env() reproduces exactly what the modules derive today."""

    def test_approved_surface_matches_audit_s3_source(self):
        ctx = sc.IssueContext.from_env(_env())
        segments = a3._require_approved_prefix(APPROVED_PREFIX)
        self.assertEqual(ctx.approved_prefix, "/".join(segments))
        self.assertEqual(ctx.approved_bucket, "edenseek-publishing")
        self.assertEqual(ctx.approved_region, "us-west-2")
        series_id, issue_id = a3._derive_identity_tail(segments)
        self.assertEqual((ctx.series_id, ctx.issue_id), (series_id, issue_id))

    def test_scout_surface_matches_report_publisher(self):
        ctx = sc.IssueContext.from_env(_env())
        norm, issue_id = srp._require_issue_prefix(SCOUT_PREFIX)
        self.assertEqual(ctx.scout_prefix, norm)
        self.assertEqual(ctx.issue_id, issue_id)
        self.assertEqual(ctx.scout_bucket, "edenseek-scout")
        self.assertEqual(ctx.scout_region, "us-west-2")

    def test_full_identity_parsed(self):
        ctx = sc.IssueContext.from_env(_env())
        self.assertEqual(ctx.identity, IDENT)

    def test_region_default_when_unset(self):
        e = _env()
        del e[sc.APPROVED_REGION_ENV]
        del e[sc.SCOUT_REGION_ENV]
        ctx = sc.IssueContext.from_env(e)
        # mirrors os.getenv(name, DEFAULT_REGION)
        self.assertEqual(ctx.approved_region, sc.DEFAULT_REGION)
        self.assertEqual(ctx.scout_region, sc.DEFAULT_REGION)

    def test_region_override_honored(self):
        ctx = sc.IssueContext.from_env(_env(**{sc.SCOUT_REGION_ENV: "eu-central-1"}))
        self.assertEqual(ctx.scout_region, "eu-central-1")

    def test_reads_process_environ_by_default(self):
        with mock.patch.dict(os.environ, _env(), clear=True):
            ctx = sc.IssueContext.from_env()
        self.assertEqual(ctx.issue_id, "issue_001")
        self.assertEqual(ctx.scout_bucket, "edenseek-scout")


class NormalizationTest(unittest.TestCase):
    """Prefix normalization strips surrounding slashes/whitespace, like the modules."""

    def test_for_prefixes_normalizes_and_validates(self):
        ctx = sc.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix="  /" + APPROVED_PREFIX + "/ ",
            scout_bucket="edenseek-scout", scout_prefix="/" + SCOUT_PREFIX + "/")
        self.assertEqual(ctx.approved_prefix, APPROVED_PREFIX)
        self.assertEqual(ctx.scout_prefix, SCOUT_PREFIX)
        self.assertEqual(ctx.identity, IDENT)

    def test_normalization_matches_modules_for_untrimmed_input(self):
        messy = "/" + SCOUT_PREFIX + "/"
        ctx = sc.IssueContext.for_prefixes(
            approved_bucket="b", approved_prefix=APPROVED_PREFIX,
            scout_bucket="edenseek-scout", scout_prefix=messy)
        norm, _ = srp._require_issue_prefix(messy)
        self.assertEqual(ctx.scout_prefix, norm)


class ConfiguredTest(unittest.TestCase):

    def test_is_configured_true(self):
        self.assertTrue(sc.IssueContext.is_configured(_env()))

    def test_is_configured_false_when_missing(self):
        e = _env()
        del e[sc.SCOUT_BUCKET_ENV]
        self.assertFalse(sc.IssueContext.is_configured(e))

    def test_is_configured_false_when_empty_string(self):
        self.assertFalse(sc.IssueContext.is_configured(_env(**{sc.SCOUT_PREFIX_ENV: ""})))


class FailLoudTest(unittest.TestCase):

    def test_missing_env_raises(self):
        e = _env()
        del e[sc.SCOUT_PREFIX_ENV]
        with self.assertRaises(sc.IssueContextError):
            sc.IssueContext.from_env(e)

    def test_empty_env_value_raises(self):
        with self.assertRaises(sc.IssueContextError):
            sc.IssueContext.from_env(_env(**{sc.APPROVED_BUCKET_ENV: ""}))

    def test_non_approved_prefix_raises(self):
        with self.assertRaises(sc.IssueContextError):
            sc.IssueContext.from_env(_env(**{sc.APPROVED_PREFIX_ENV: SCOUT_PREFIX}))  # no /approved

    def test_scout_prefix_without_issues_raises(self):
        bad = "publishers/edenseek/title_groups/society_universe/series/society_of_killers"
        with self.assertRaises(sc.IssueContextError):
            sc.IssueContext.from_env(_env(**{sc.SCOUT_PREFIX_ENV: bad}))

    def test_scout_prefix_not_ending_at_issue_raises(self):
        bad = SCOUT_PREFIX + "/reports"
        with self.assertRaises(sc.IssueContextError):
            sc.IssueContext.from_env(_env(**{sc.SCOUT_PREFIX_ENV: bad}))

    def test_identity_mismatch_between_prefixes_raises(self):
        other = ("publishers/edenseek/title_groups/society_universe/series/society_of_killers/"
                 "issues/issue_002")
        with self.assertRaises(sc.IssueContextError):
            sc.IssueContext.from_env(_env(**{sc.SCOUT_PREFIX_ENV: other}))  # issue_002 vs approved issue_001


class ForwardFieldsAndImmutabilityTest(unittest.TestCase):

    def test_forward_fields_default_inert(self):
        ctx = sc.IssueContext.from_env(_env())
        self.assertIsNone(ctx.revision)
        self.assertEqual(ctx.trigger, sc.DEFAULT_TRIGGER)
        self.assertIsNone(ctx.methodology)
        self.assertIsNone(ctx.analyzer_registry)
        self.assertIsNone(ctx.schedule)

    def test_from_env_carries_revision_and_trigger(self):
        ctx = sc.IssueContext.from_env(_env(), revision="rev_0be8dc34", trigger="certification")
        self.assertEqual(ctx.revision, "rev_0be8dc34")
        self.assertEqual(ctx.trigger, "certification")

    def test_frozen_cannot_mutate(self):
        ctx = sc.IssueContext.from_env(_env())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            ctx.issue_id = "hacked"  # type: ignore[misc]

    def test_derive_returns_modified_copy(self):
        base = sc.IssueContext.from_env(_env())
        derived = base.derive(revision="rev_abc", trigger="reconciliation")
        self.assertEqual(derived.revision, "rev_abc")
        self.assertEqual(derived.trigger, "reconciliation")
        # base is untouched (immutable); identity + config carried over
        self.assertIsNone(base.revision)
        self.assertEqual(derived.issue_id, base.issue_id)
        self.assertEqual(derived.scout_prefix, base.scout_prefix)


if __name__ == "__main__":
    unittest.main()
