"""Anti-corruption boundary between the Publisher's emitted Review Record contract
and Scout's own canonical delta model (Week 11 Increment 6.3, Phase A).

This is the SINGLE module that knows the Publisher-emitted shapes:
  * C — Review Record   (`reviews/{review_id}/review_report.json`)
  * D — Platform Approval (`reviews/{review_id}/platform_approval.json`)
  * B — Generated PAL    (`processing/generated/<gen_rev>/generated_snapshot.json`)

Everything downstream in the Scout delta pipeline (`delta_geometry`, `delta_metadata`,
`delta_ledger`, `delta_auditor`) operates ONLY on the canonical model produced here — no
Publisher representation detail (page-keyed `panels[]`, `[x,y,w,h]` vs `{x,y,width,height}`,
field names) leaks past this boundary. If the Publisher reshapes its emission, only this
module changes.

**Versioned + fail-fast (founder directive).** Scout pins the Publisher contract versions it
understands. An unrecognized `review_report_version` / `platform_approval_version` /
`generated_snapshot_version`, or a missing/malformed required field, raises
``ReviewContractError`` at this boundary — Scout never silently reinterprets an unknown
contract. See ``docs/architecture/REVIEW_RECORD_INPUT_CONTRACT.md``.

Read-only / offline: this module only transforms already-parsed JSON dicts. It performs no
S3, no LLM/vision, no network — deterministic over frozen inputs.
"""
from logging_config import logger

# ---- Pinned Publisher contract versions Scout understands (fail-fast on any other) ----
SUPPORTED_REVIEW_REPORT_VERSIONS = frozenset({"v1"})
SUPPORTED_PLATFORM_APPROVAL_VERSIONS = frozenset({"v1"})
SUPPORTED_GENERATED_SNAPSHOT_VERSIONS = frozenset({"v1"})

# The Publisher's sentinel for a manual (non-generated) publication.
MANUAL_SENTINEL = "not_applicable_manual_publication"
GENERATED_PUBLICATION_STATE = "generated_publication"

# The version of Scout's normalization (this anti-corruption boundary): how Publisher shapes are
# mapped to Scout's canonical geometry/metadata model. It is a comparability axis — a change here
# can shift metrics without any Publisher or algorithm change (see SCOUT_REPORT_INDEX.md).
NORMALIZATION_VERSION = "v1"

# Canonical dataset states, reported VERBATIM from the Publisher (Scout never sets these).
STATE_DRAFT = "draft"
STATE_CREATOR_APPROVED = "creator_approved"
STATE_EDENSEEK_APPROVED = "edenseek_approved"

# Applicability of a generated-vs-approved comparison for a publication.
APPLICABILITY_GENERATED = "generated_publication"
APPLICABILITY_MANUAL = "manual"

# Known STRUCTURAL sibling keys that live inside the approved_geometry map alongside the
# artifact-id-keyed panel entries (Publisher-emitted, verified against production
# rev_a8c65a83a196). They are ordering/collection metadata, NOT panel geometry, and are
# skipped. Any OTHER non-artifact member is unknown and fails fast (never silently reinterpreted).
APPROVED_GEOMETRY_STRUCTURAL_KEYS = frozenset({"panel_order", "spread_artifacts"})


class ReviewContractError(Exception):
    """Raised at the anti-corruption boundary when the Publisher-emitted Review Record
    contract is an unrecognized version or is missing/malformed a required field.

    Fail-fast by design: Scout refuses to reinterpret an unknown contract rather than
    silently producing a wrong delta.
    """


def _require(obj, key, source):
    if not isinstance(obj, dict):
        raise ReviewContractError(f"{source}: expected a JSON object, got {type(obj).__name__}")
    if key not in obj:
        raise ReviewContractError(f"{source}: missing required key '{key}'")
    return obj[key]


def _require_version(value, supported, name):
    if value not in supported:
        logger.error(
            "Review Record contract version mismatch: %s=%r not in supported %s "
            "(fail-fast — refusing to reinterpret an unknown Publisher contract)",
            name, value, sorted(supported),
        )
        raise ReviewContractError(
            f"unsupported {name}={value!r}; Scout understands {sorted(supported)}. "
            "The Publisher contract changed — update the anti-corruption adapter and "
            "REVIEW_RECORD_INPUT_CONTRACT.md, do not silently reinterpret."
        )
    return value


def _f(value, default=0.0):
    """Coerce a numeric to float deterministically; non-numeric -> default."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normalize_bbox(raw, source):
    """Normalize either emitted bbox representation to a canonical ``(x, y, w, h)`` of floats.

    Accepts the generated side's ``[x, y, w, h]`` list and the approved side's
    ``{x, y, width, height}`` object. Missing dimensions default to 0.0 (a degenerate box
    yields IoU 0 downstream — never a silent match).
    """
    if isinstance(raw, (list, tuple)):
        if len(raw) < 4:
            raise ReviewContractError(f"{source}: bbox list must have 4 elements, got {raw!r}")
        return (_f(raw[0]), _f(raw[1]), _f(raw[2]), _f(raw[3]))
    if isinstance(raw, dict):
        return (_f(raw.get("x")), _f(raw.get("y")),
                _f(raw.get("width", raw.get("w"))), _f(raw.get("height", raw.get("h"))))
    raise ReviewContractError(f"{source}: unrecognized bbox representation {type(raw).__name__}")


def _geometry_flags(entry):
    """Preserve (not interpret) the approved-side per-artifact flags. Downstream applies
    semantics (e.g. a deleted panel is excluded from the approved set)."""
    flags = {}
    for src_key, canon_key in (("approved", "approved"), ("deleted", "deleted"),
                               ("isNew", "is_new"), ("is_new", "is_new")):
        if isinstance(entry, dict) and src_key in entry:
            flags[canon_key] = bool(entry[src_key])
    return flags


def _normalize_generated_geometry(generated_panel_geometry):
    """Flatten the generated side's 6-key summary object into Scout's canonical
    ``{artifact_id: {bbox, page_number, coordinate_space, flags}}`` map, keyed by each
    panel row's ``panel_key`` (== the approved-side ``artifact_id``).

    Geometry is normalized from the row's **``bounds``** (normalized 0..1
    ``{x,y,width,height}`` — the exact representation the approved side uses), NOT ``bbox``
    (which is pixel ``[x1,y1,x2,y2]`` corners and would compare falsely; kept as pixel
    provenance only). Fail-fast if ``bounds`` is absent — a real contract violation
    (Publisher-confirmed present on every panel).
    """
    panels = _require(generated_panel_geometry, "panels", "generated_panel_geometry")
    if not isinstance(panels, list):
        raise ReviewContractError("generated_panel_geometry.panels must be a list")
    canon = {}
    for i, row in enumerate(panels):
        src = f"generated_panel_geometry.panels[{i}]"
        artifact_id = _require(row, "panel_key", src)
        if not isinstance(artifact_id, str):
            raise ReviewContractError(f"{src}.panel_key must be a string")
        canon[artifact_id] = {
            "bbox": _normalize_bbox(_require(row, "bounds", src), src + ".bounds"),
            "page_number": row.get("page_number"),
            "coordinate_space": row.get("coordinate_space"),
            "flags": {},  # generated side carries no approval flags
        }
    return canon


def _normalize_approved_geometry(approved_geometry):
    """Normalize the approved side's flat ``{artifact_id: {...}}`` map into Scout's canonical
    geometry map (flags preserved, not interpreted).

    The map ALSO carries known structural sibling keys (``panel_order``, ``spread_artifacts``)
    that are not panel geometry — those are skipped; any other non-artifact member fails fast.

    Three panel representations exist. A normal page panel carries normalized 0..1
    ``{x,y,width,height}``. A **spread** panel (``isSpreadPanel: true``) carries **degenerate
    page coordinates (0.01/absent)** and its real geometry in **``stage_geometry``** (spread-
    canvas space) with a ``page_range`` — for those we use ``stage_geometry`` and flag
    ``is_spread`` (spreads are drawn, have no generated counterpart, and are handled as
    approved-only/missing downstream — never IoU-matched). Spread panels appear both as
    ``spread_<pages>::pN`` entries and as ``<page>::NEW::N`` drawn-on-spread entries; both carry
    ``isSpreadPanel`` and are handled identically."""
    if not isinstance(approved_geometry, dict):
        raise ReviewContractError("approved_geometry must be a JSON object (artifact_id map)")
    canon = {}
    for artifact_id, entry in approved_geometry.items():
        if artifact_id in APPROVED_GEOMETRY_STRUCTURAL_KEYS:
            continue  # ordering/collection sibling, not a panel — not Scout's to compare
        src = f"approved_geometry[{artifact_id!r}]"
        if not isinstance(entry, dict):
            raise ReviewContractError(
                f"{src}: expected an artifact geometry object, got {type(entry).__name__} "
                "(unknown non-artifact member of approved_geometry — refusing to reinterpret)")
        is_spread = bool(entry.get("isSpreadPanel"))
        flags = _geometry_flags(entry)
        page_range = None
        if is_spread:
            flags["is_spread"] = True
            page_range = entry.get("page_range")
            stage = entry.get("stage_geometry")
            if not isinstance(stage, dict):
                raise ReviewContractError(
                    f"{src}: isSpreadPanel with no stage_geometry (spread-canvas geometry required)")
            bbox = _normalize_bbox(stage, src + ".stage_geometry")
        elif any(k in entry for k in ("x", "y", "width", "height")):
            bbox = _normalize_bbox(entry, src)
        else:
            raise ReviewContractError(
                f"{src}: not a recognized panel geometry (no x/y/width/height and not a spread) "
                "— unexpected approved_geometry member; refusing to reinterpret")
        canon[artifact_id] = {
            "bbox": bbox,
            "page_number": entry.get("page_number") if isinstance(entry, dict) else None,
            "coordinate_space": "spread" if is_spread else (
                entry.get("coordinate_space") if isinstance(entry, dict) else None),
            "flags": flags,
            "page_range": page_range,
        }
    return canon


def _extract_content_fields(output_obj):
    """The exactly-four comparable metadata content fields, from the nested ``output`` subtree
    (Publisher-confirmed). Provenance (``context_source``, ``geometry_source``) and plumbing
    (``status``/``version``/``metadata_locked``/``metadata_review_state``) are NOT content and
    are excluded. ``classification.tags`` is taken AS-IS and never shape-assumed — it is normally
    a ``{action,mood,setting}`` dict on BOTH sides (Publisher census 94-95/97), rarely a flat
    ``list<str>`` (a human edit), and may be ``null`` — so the delta classifies dict==dict as an
    accept, a dict-vs-list (or any change) as an edit, and null==null as a no-op."""
    o = output_obj if isinstance(output_obj, dict) else {}
    classification = o.get("classification") or {}
    entities = o.get("entities") or {}
    narrative = o.get("narrative") or {}
    return {
        "classification.tags": classification.get("tags"),
        "entities.characters": entities.get("characters"),
        "narrative.dialogue": narrative.get("dialogue"),
        "narrative.summary": narrative.get("summary"),
    }


def _normalize_metadata(metadata_obj, side):
    """Normalize a ``{llm_enrichment_output_version, llm_enrichment_outputs:[...]}`` object
    into Scout's canonical ``{artifact_id: {schema_version, fields}}`` map, where ``fields`` is
    exactly the four content fields extracted from each output's nested ``output`` subtree. The
    schema version is carried so the metadata delta can enforce schema-version scoping."""
    if not isinstance(metadata_obj, dict):
        raise ReviewContractError(f"{side} metadata must be a JSON object")
    schema_version = metadata_obj.get("llm_enrichment_output_version")
    outputs = metadata_obj.get("llm_enrichment_outputs", [])
    if not isinstance(outputs, list):
        raise ReviewContractError(f"{side} metadata.llm_enrichment_outputs must be a list")
    canon = {}
    for i, out in enumerate(outputs):
        src = f"{side} metadata.llm_enrichment_outputs[{i}]"
        artifact_id = _require(out, "artifact_id", src)
        canon[artifact_id] = {"schema_version": schema_version,
                              "fields": _extract_content_fields(out.get("output"))}
    return canon


def _generated_summary(generated_panel_geometry):
    """The generated side's page/panel totals (for per-page benchmark denominators). Best-effort:
    missing fields are ``None``, never fabricated."""
    g = generated_panel_geometry if isinstance(generated_panel_geometry, dict) else {}
    return {"total_pages": g.get("total_pages"),
            "total_story_pages": g.get("total_story_pages"),
            "total_panels": g.get("total_panels")}


def _metadata_provenance(generated_metadata, approved_metadata):
    """Metadata generation provenance for the comparability contract — enrichment schema versions
    on both sides, plus prompt/model identifiers WHEN the Publisher emits them (else ``None``).

    Security: only identifiers/versions are captured — never prompt bodies, secrets, or credentials.
    """
    gm = generated_metadata if isinstance(generated_metadata, dict) else {}
    am = approved_metadata if isinstance(approved_metadata, dict) else {}
    # Prompt/model identifiers are optional and Publisher-emitted; probe a few known field names.
    def pick(obj, *names):
        for n in names:
            if isinstance(obj, dict) and obj.get(n) not in (None, ""):
                return obj[n]
        return None
    return {
        "generated_schema_version": gm.get("llm_enrichment_output_version"),
        "approved_schema_version": am.get("llm_enrichment_output_version"),
        "prompt_id": pick(gm, "prompt_id", "enrichment_prompt_id"),
        "prompt_version": pick(gm, "prompt_version", "enrichment_prompt_version"),
        "model": pick(gm, "model", "enrichment_model", "llm_model"),
        "provider": pick(gm, "provider", "model_provider", "llm_provider"),
    }


def _publisher_certified(platform_approval, published_something):
    """The Publisher/Platform's OWN certified signal, carried verbatim — kept strictly
    separate from Scout's independent delta. Absence of D ⇒ ``creator_approved`` (published,
    not yet platform-approved); if nothing was published, ``draft``."""
    if platform_approval is None:
        state = STATE_CREATOR_APPROVED if published_something else STATE_DRAFT
        return {"canonical_dataset_state": state, "platform_readiness": None,
                "certifies_review_report_key": None, "source": "absent (no platform_approval.json)"}
    _require_version(
        _require(platform_approval, "platform_approval_version", "platform_approval.json"),
        SUPPORTED_PLATFORM_APPROVAL_VERSIONS, "platform_approval_version",
    )
    return {
        "canonical_dataset_state": _require(platform_approval, "canonical_dataset_state",
                                            "platform_approval.json"),
        "platform_readiness": platform_approval.get("readiness"),
        "certifies_review_report_key": platform_approval.get("certifies_review_report_key"),
        "state_transition": platform_approval.get("state_transition"),
        "platform_authority": platform_approval.get("platform_authority"),
        "source": "platform_approval.json",
    }


def adapt_review(review_report, platform_approval=None, generated_snapshot=None):
    """Translate the Publisher-emitted contract (C, optional D, optional B) into Scout's
    canonical ``CanonicalReview`` model. Fail-fast on version/shape violations.

    Returns a dict::

        {
          "review_id", "published_revision_id",
          "generated_snapshot_revision_id": str | None,
          "applicability": "generated_publication" | "manual",
          "generated": {"geometry": CanonicalGeometry, "metadata": CanonicalMetadata} | None,
          "approved":  {"geometry": CanonicalGeometry, "metadata": CanonicalMetadata},
          "publisher_certified": {...},          # verbatim Publisher/Platform signal
          "source_versions": {...},
        }
    """
    _require_version(
        _require(review_report, "review_report_version", "review_report.json"),
        SUPPORTED_REVIEW_REPORT_VERSIONS, "review_report_version",
    )
    review_id = _require(review_report, "review_id", "review_report.json")
    provenance = _require(review_report, "provenance", "review_report.json")
    published_revision_id = _require(provenance, "published_revision_id", "review_report.provenance")
    gen_vs_approved = _require(provenance, "generated_vs_approved", "review_report.provenance")

    approved = {
        "geometry": _normalize_approved_geometry(
            _require(review_report, "approved_geometry", "review_report.json")),
        "metadata": _normalize_metadata(
            _require(review_report, "approved_metadata", "review_report.json"), "approved"),
    }

    # Applicability + the generated side. Manual publications are NOT-APPLICABLE — never a
    # zero-delta — and carry a null generated side.
    generated = None
    generated_snapshot_revision_id = None
    if gen_vs_approved == MANUAL_SENTINEL:
        applicability = APPLICABILITY_MANUAL
    elif isinstance(gen_vs_approved, dict) and gen_vs_approved.get("state") == GENERATED_PUBLICATION_STATE:
        applicability = APPLICABILITY_GENERATED
        generated_snapshot_revision_id = gen_vs_approved.get("generated_snapshot_revision_id")
        gen_geom_raw = review_report.get("generated_geometry")
        gen_meta_raw = review_report.get("generated_metadata")
        if gen_geom_raw is None or gen_meta_raw is None:
            raise ReviewContractError(
                "generated_publication must carry non-null generated_geometry + generated_metadata "
                f"(review_id={review_id})")
        generated = {
            "geometry": _normalize_generated_geometry(gen_geom_raw),
            "metadata": _normalize_metadata(gen_meta_raw, "generated"),
            "summary": _generated_summary(gen_geom_raw),
        }
    else:
        raise ReviewContractError(
            f"unrecognized provenance.generated_vs_approved={gen_vs_approved!r} "
            f"(review_id={review_id}) — expected the manual sentinel or a "
            "generated_publication object")

    # Optional B cross-check (advisory): if the Generated PAL is supplied, its version must be
    # understood and its rev must match the link. Fail-fast on a version we don't know.
    if generated_snapshot is not None:
        _require_version(
            _require(generated_snapshot, "generated_snapshot_version", "generated_snapshot.json"),
            SUPPORTED_GENERATED_SNAPSHOT_VERSIONS, "generated_snapshot_version",
        )

    return {
        "review_id": review_id,
        "published_revision_id": published_revision_id,
        "generated_snapshot_revision_id": generated_snapshot_revision_id,
        "applicability": applicability,
        "generated": generated,
        "approved": approved,
        "publisher_certified": _publisher_certified(platform_approval, published_something=True),
        "normalization_version": NORMALIZATION_VERSION,
        "metadata_provenance": _metadata_provenance(
            review_report.get("generated_metadata"), review_report.get("approved_metadata")),
        "source_versions": {
            "review_report_version": review_report.get("review_report_version"),
            "platform_approval_version": (platform_approval or {}).get("platform_approval_version"),
            "generated_snapshot_version": (generated_snapshot or {}).get("generated_snapshot_version"),
            "generated_metadata_version": (review_report.get("generated_metadata") or {}).get(
                "llm_enrichment_output_version"),
            "approved_metadata_version": (review_report.get("approved_metadata") or {}).get(
                "llm_enrichment_output_version"),
        },
    }
