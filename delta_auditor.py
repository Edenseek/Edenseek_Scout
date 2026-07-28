"""Scout Synchronization Audit orchestrator (Week 11 Increment 6.3, Phase A).

Parallel to ``dataset_auditor`` but for the generated-vs-approved delta family. Consumes the
Publisher's emitted Review Record (C), optional Platform Approval (D), and optional Generated
PAL (B) — as already-parsed JSON dicts — through the single anti-corruption boundary
(``review_contract_adapter``), then computes Scout's independent, deterministic, advisory
delta on Scout's own canonical model.

Phase A is OFFLINE: this module takes parsed dicts (fixtures/tests) and returns a report; it
does not read ``reviews/`` from S3 (Phase B, gated on the Publisher read grant) and never
publishes or mutates anything. No LLM/vision/network.

Scout's independent delta (``geometry_delta`` / ``metadata_delta`` / ``correction_ledger``) is
kept STRICTLY SEPARATE from ``publisher_certified_state`` — the Publisher/Platform's own
certified canonical state + readiness, carried verbatim. Scout measures and reports; the
Publisher certifies.
"""
import json

from review_contract_adapter import adapt_review
from delta_geometry import compute_geometry_delta
from delta_metadata import compute_metadata_delta
from delta_ledger import build_correction_ledger

SCOUT_DELTA_REPORT_VERSION = "v1"


def run_delta_audit(review_report, platform_approval=None, generated_snapshot=None):
    """Run the deterministic Scout Synchronization Audit for one publication.

    ``review_report`` (C) is required; ``platform_approval`` (D) and ``generated_snapshot`` (B)
    are optional parsed dicts. Returns the provenance-stamped Scout delta report. Raises
    ``ReviewContractError`` (from the adapter) on an unrecognized/malformed Publisher contract.
    """
    canonical = adapt_review(review_report, platform_approval, generated_snapshot)
    geometry_delta = compute_geometry_delta(canonical)
    metadata_delta = compute_metadata_delta(canonical)
    correction_ledger = build_correction_ledger(geometry_delta, metadata_delta)

    return {
        "scout_delta_report_version": SCOUT_DELTA_REPORT_VERSION,
        "review_id": canonical["review_id"],
        "applicability": canonical["applicability"],
        "provenance": {
            "review_id": canonical["review_id"],
            "published_revision_id": canonical["published_revision_id"],
            "generated_snapshot_revision_id": canonical["generated_snapshot_revision_id"],
            "source_versions": canonical["source_versions"],
        },
        # --- Scout's INDEPENDENT, advisory measurement (never authoritative) ---
        "geometry_delta": geometry_delta,
        "metadata_delta": metadata_delta,
        "correction_ledger": correction_ledger,
        # --- The Publisher/Platform's OWN certified signal, verbatim, kept SEPARATE ---
        "publisher_certified_state": canonical["publisher_certified"],
    }


def serialize_delta_report(report):
    """Canonical, byte-reproducible JSON serialization (deterministic across runs for identical
    inputs). Suitable for the Phase-B publish to ``edenseek-scout``."""
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
