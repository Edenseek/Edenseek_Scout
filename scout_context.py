"""scout_context.py — the canonical ``IssueContext`` execution context.

Phase 1 (behavior-neutral). This module introduces ``IssueContext``: the single value
object that resolves Scout's per-issue execution configuration from the environment,
reproducing **byte-for-byte** the bucket / prefix / region / identity that the existing
modules derive today (``audit_s3_source`` for the approved read surface, and
``scout_report_publisher`` / ``scout_report_index`` / ``scout_revision_ledger`` for the
Scout write surface).

Design constraints (ADR-0001 + PHASE_1 runbook):

* **Leaf module.** ``scout_context`` imports only the standard library (plus the shared
  logger). It depends on *no* Scout module, so every other module can eventually depend on
  *it* without an import cycle. This is what lets later increments thread ``context`` through
  the read path, persistence, ledger, runners, and projections.
* **Nothing consumes it in Phase 1.** Introducing the abstraction changes no production
  behavior; the equivalence is proven by tests that compare ``IssueContext.from_env()`` to
  the modules' own derivations for the same environment.
* **Fail-loud.** ``from_env()`` raises ``IssueContextError`` on missing/invalid config rather
  than silently defaulting to a different issue — the same posture as the modules it mirrors.

Long-term role. ``IssueContext`` is intended to become the canonical execution context for
*every* audit, carrying the full ownership identity (publisher / title group / series / issue),
the ``revision`` under audit, the ``methodology`` fingerprint, and the execution ``trigger``.
Later phases attach the ``analyzer_registry`` (Audit orchestration) and ``schedule`` (scheduled
execution) that the Discovery -> Registry -> Audit -> Publication architecture is built on. Those
forward fields exist here as inert, defaulted slots; they carry no behavior in Phase 1.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional

from logging_config import logger

# --- Environment contract (mirrors the modules; the test suite guards against drift) --------
# Approved-Dataset read surface (edenseek-publishing, read-only) — cf. audit_s3_source.
APPROVED_BUCKET_ENV = "SCOUT_APPROVED_S3_BUCKET"
APPROVED_PREFIX_ENV = "SCOUT_APPROVED_S3_PREFIX"
APPROVED_REGION_ENV = "SCOUT_APPROVED_S3_REGION"
# Scout Repository write surface (edenseek-scout, read/write) — cf. scout_report_publisher.
SCOUT_BUCKET_ENV = "SCOUT_REPO_S3_BUCKET"
SCOUT_PREFIX_ENV = "SCOUT_REPO_S3_PREFIX"
SCOUT_REGION_ENV = "SCOUT_REPO_S3_REGION"

DEFAULT_REGION = "us-west-2"          # cf. audit_s3_source.DEFAULT_REGION / srp.DEFAULT_REGION
DEFAULT_TRIGGER = "manual"            # cf. scout_delta_audit.audit_current_revision(trigger=...)

# Canonical ownership-chain keys -> identity fields (publishers/{}/title_groups/{}/series/{}/issues/{}).
_CHAIN_KEYS = (
    ("publishers", "publisher_id"),
    ("title_groups", "title_group_id"),
    ("series", "series_id"),
    ("issues", "issue_id"),
)


class IssueContextError(Exception):
    """Raised when the execution context cannot be resolved (missing/invalid configuration)."""


def _split(prefix: str) -> list[str]:
    """Normalize a prefix to path segments exactly as the modules do: strip, trim '/', split."""
    return prefix.strip().strip("/").split("/")


def _derive_identity(segments: list[str]) -> dict[str, Optional[str]]:
    """Extract the ownership identity from a chain, tolerating absent leading levels.

    Returns a dict keyed by the canonical identity fields; a level absent from the chain maps
    to ``None`` (so a shorter approved surface without ``publishers/`` still yields series+issue).
    """
    ident: dict[str, Optional[str]] = {fieldname: None for _key, fieldname in _CHAIN_KEYS}
    for key, fieldname in _CHAIN_KEYS:
        if key in segments:
            i = segments.index(key)
            if i + 1 < len(segments):
                ident[fieldname] = segments[i + 1]
    return ident


def _normalize_approved_prefix(prefix: str) -> tuple[str, dict[str, Optional[str]]]:
    """Validate + normalize the approved read prefix (mirrors audit_s3_source).

    Enforces the ``approved/`` surface and the canonical ``series/.../issues/`` chain, returning
    ``(normalized_prefix, identity)``.
    """
    segments = _split(prefix)
    if not segments or segments[-1] != "approved":
        raise IssueContextError(
            f"Refusing non-approved S3 prefix (must end with 'approved/'): {prefix!r}"
        )
    ident = _derive_identity(segments)
    if ident["series_id"] is None or ident["issue_id"] is None:
        raise IssueContextError(
            f"Approved prefix missing the canonical series/issues chain: {'/'.join(segments)!r}"
        )
    return "/".join(segments), ident


def _normalize_scout_prefix(prefix: str) -> tuple[str, dict[str, Optional[str]]]:
    """Validate + normalize the Scout write prefix (mirrors scout_report_publisher._require_issue_prefix).

    Enforces the per-issue ownership chain ``publishers/.../issues/{issue_id}`` ending at the issue,
    returning ``(normalized_prefix, identity)``.
    """
    segments = _split(prefix)
    ident = _derive_identity(segments)
    issue_id = ident["issue_id"]
    if issue_id is None:
        raise IssueContextError(
            f"Refusing Scout Repository prefix without an 'issues/{{issue_id}}' chain: {prefix!r}"
        )
    if "publishers" not in segments or segments[-1] != issue_id:
        raise IssueContextError(
            "Scout Repository prefix must be the issue ownership-chain root "
            f"'publishers/.../issues/{{issue_id}}': {prefix!r}"
        )
    return "/".join(segments), ident


def _merge_identity(approved: Mapping[str, Optional[str]],
                    scout: Mapping[str, Optional[str]]) -> dict[str, Optional[str]]:
    """Reconcile identities derived from the two prefixes into one, failing loud on conflict.

    The Scout write chain is the fuller ownership root (it carries publishers/title_groups), so it
    is preferred; the approved surface contributes series/issue. Any field present in *both* must
    agree — a mismatch means the two prefixes point at different issues (a misconfiguration).
    """
    merged: dict[str, Optional[str]] = {}
    for _key, fieldname in _CHAIN_KEYS:
        a, s = approved.get(fieldname), scout.get(fieldname)
        if a is not None and s is not None and a != s:
            raise IssueContextError(
                f"Approved and Scout prefixes disagree on {fieldname}: "
                f"approved={a!r} vs scout={s!r}"
            )
        merged[fieldname] = s if s is not None else a
    return merged


@dataclass(frozen=True)
class IssueContext:
    """Immutable, canonical execution context for a single issue's audit.

    Phase 1 carries the resolved S3 configuration + ownership identity — everything the current
    read/write/index/ledger paths derive from the environment today. ``revision``, ``trigger`` and
    ``methodology`` are carried but not yet consumed; ``analyzer_registry`` and ``schedule`` are
    forward slots for later phases and remain ``None`` in Phase 1.
    """
    # Ownership identity (canonical keys, consistent with the codebase-wide identity dict).
    publisher_id: Optional[str]
    title_group_id: Optional[str]
    series_id: Optional[str]
    issue_id: Optional[str]

    # Approved-Dataset read surface (edenseek-publishing, read-only).
    approved_bucket: str
    approved_prefix: str
    approved_region: str

    # Scout Repository write surface (edenseek-scout, read/write).
    scout_bucket: str
    scout_prefix: str
    scout_region: str

    # Forward-looking execution fields (carried; inert in Phase 1).
    revision: Optional[str] = None
    trigger: str = DEFAULT_TRIGGER
    methodology: Optional[Mapping[str, Any]] = None
    analyzer_registry: Optional[Any] = None   # attached by the Audit-orchestration phase
    schedule: Optional[Any] = None            # attached by the scheduled-execution phase

    @property
    def identity(self) -> dict[str, Optional[str]]:
        """The ownership identity as the canonical dict used across the codebase."""
        return {
            "publisher_id": self.publisher_id,
            "title_group_id": self.title_group_id,
            "series_id": self.series_id,
            "issue_id": self.issue_id,
        }

    @classmethod
    def is_configured(cls, env: Optional[Mapping[str, str]] = None) -> bool:
        """True only when both the approved read and Scout write surfaces are configured.

        Mirrors the modules' ``is_configured()`` (a bucket+prefix each; empty string is falsy).
        """
        env = os.environ if env is None else env
        return bool(env.get(APPROVED_BUCKET_ENV) and env.get(APPROVED_PREFIX_ENV)
                    and env.get(SCOUT_BUCKET_ENV) and env.get(SCOUT_PREFIX_ENV))

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None,
                 *, revision: Optional[str] = None, trigger: str = DEFAULT_TRIGGER,
                 methodology: Optional[Mapping[str, Any]] = None) -> "IssueContext":
        """Resolve the context from the environment, reproducing the modules' derivation exactly.

        Reads the same env vars, applies the same region default, and runs the same prefix
        validation/normalization as ``audit_s3_source`` and ``scout_report_publisher``. Fails loud
        (``IssueContextError``) on any missing bucket/prefix or invalid prefix, rather than
        silently auditing a different issue.
        """
        env = os.environ if env is None else env

        approved_bucket = env.get(APPROVED_BUCKET_ENV)
        approved_prefix = env.get(APPROVED_PREFIX_ENV)
        scout_bucket = env.get(SCOUT_BUCKET_ENV)
        scout_prefix = env.get(SCOUT_PREFIX_ENV)
        missing = [name for name, val in (
            (APPROVED_BUCKET_ENV, approved_bucket), (APPROVED_PREFIX_ENV, approved_prefix),
            (SCOUT_BUCKET_ENV, scout_bucket), (SCOUT_PREFIX_ENV, scout_prefix),
        ) if not val]
        if missing:
            raise IssueContextError(
                "IssueContext is not fully configured; missing/empty: " + ", ".join(missing)
            )

        norm_approved, approved_ident = _normalize_approved_prefix(approved_prefix)
        norm_scout, scout_ident = _normalize_scout_prefix(scout_prefix)
        identity = _merge_identity(approved_ident, scout_ident)

        # os.getenv(name, DEFAULT) semantics: an absent key -> default; a present empty value stays "".
        approved_region = env.get(APPROVED_REGION_ENV, DEFAULT_REGION)
        scout_region = env.get(SCOUT_REGION_ENV, DEFAULT_REGION)

        ctx = cls(
            publisher_id=identity["publisher_id"], title_group_id=identity["title_group_id"],
            series_id=identity["series_id"], issue_id=identity["issue_id"],
            approved_bucket=approved_bucket, approved_prefix=norm_approved,
            approved_region=approved_region,
            scout_bucket=scout_bucket, scout_prefix=norm_scout, scout_region=scout_region,
            revision=revision, trigger=trigger, methodology=methodology,
        )
        logger.debug("IssueContext.from_env resolved issue=%s (approved=s3://%s/%s, scout=s3://%s/%s)",
                     ctx.issue_id, ctx.approved_bucket, ctx.approved_prefix,
                     ctx.scout_bucket, ctx.scout_prefix)
        return ctx

    @classmethod
    def for_prefixes(cls, *, approved_bucket: str, approved_prefix: str,
                     scout_bucket: str, scout_prefix: str,
                     approved_region: str = DEFAULT_REGION, scout_region: str = DEFAULT_REGION,
                     revision: Optional[str] = None, trigger: str = DEFAULT_TRIGGER,
                     methodology: Optional[Mapping[str, Any]] = None) -> "IssueContext":
        """Construct a context from explicit prefixes (tests + future multi-issue callers).

        Applies the same validation/normalization as ``from_env`` but takes no environment; this is
        the seam a future Discovery/Registry layer uses to build a context per enumerated issue.
        """
        norm_approved, approved_ident = _normalize_approved_prefix(approved_prefix)
        norm_scout, scout_ident = _normalize_scout_prefix(scout_prefix)
        identity = _merge_identity(approved_ident, scout_ident)
        return cls(
            publisher_id=identity["publisher_id"], title_group_id=identity["title_group_id"],
            series_id=identity["series_id"], issue_id=identity["issue_id"],
            approved_bucket=approved_bucket, approved_prefix=norm_approved,
            approved_region=approved_region,
            scout_bucket=scout_bucket, scout_prefix=norm_scout, scout_region=scout_region,
            revision=revision, trigger=trigger, methodology=methodology,
        )

    def derive(self, **changes: Any) -> "IssueContext":
        """Return a copy with fields overridden (e.g. attaching ``revision``/``trigger``).

        The context is immutable; ``derive`` is how later phases specialize a base context (per
        revision, per trigger) without mutating the shared instance.
        """
        return replace(self, **changes)
