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
import hashlib

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


def _derive_page_number(artifact_id, carried):
    """The page scope a page-panel belongs to — the scope within which its geometry may be compared.
    Panel coordinates are normalized **per page**, so a same-position panel on another page is a
    different panel; matching must be page-scoped (see delta_geometry v2 and
    docs/phases/geometry-correctness/).

    Prefer the Publisher-carried ``page_number`` (int); else derive from the artifact-id identity,
    which encodes the page (``<property>_<issue>_<page>::pN`` and ``<page>::NEW::N``). If the id
    carries no numeric page (e.g. a ``cover`` label), fall back to the id's page component **as a
    string scope** so panels on that page still group together — never aborting the whole delta over
    one un-numbered page. Both sides use the same id scheme, so matched panels share the scope.
    """
    if carried is not None:
        try:
            return int(carried)
        except (TypeError, ValueError):
            pass
    head = str(artifact_id).split("::", 1)[0]
    if head.isdigit():
        return int(head)                       # "<page>::NEW::N" form
    nums = [tok for tok in head.split("_") if tok.isdigit()]
    if nums:
        return int(nums[-1])                   # "<property>_<issue>_<page>" -> trailing = page
    return head                                # non-numeric page label -> group by page component


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
        coord = row.get("coordinate_space")
        is_spread = coord == "spread"
        canon[artifact_id] = {
            "artifact_id": artifact_id,
            "bbox": _normalize_bbox(_require(row, "bounds", src), src + ".bounds"),
            # Page panels get a page scope; spreads are matched by page_range, not page_number, so
            # (like the approved side) leave theirs as carried — symmetric handling.
            "page_number": (row.get("page_number") if is_spread
                            else _derive_page_number(artifact_id, row.get("page_number"))),
            "coordinate_space": coord,
            # Generated spreads (spread-canvas frame) are flagged so the geometry delta matches them
            # spread-to-spread instead of against page panels; page-space rows carry no flags.
            "flags": {"is_spread": True} if is_spread else {},
            "page_range": row.get("page_range"),
            "order": row.get("order"),   # automated reading order within the page (for order fidelity)
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
    # The human-approved reading order per page (``panel_order`` = {page: [ordered artifact_ids]}).
    # Previously skipped as a structural sibling; captured here as each panel's position so the delta
    # can measure reading-order fidelity (generated order vs approved order among matched panels).
    _panel_order = approved_geometry.get("panel_order")
    order_of = {}
    if isinstance(_panel_order, dict):
        for _ids in _panel_order.values():
            if isinstance(_ids, list):
                for _i, _aid in enumerate(_ids):
                    order_of[_aid] = _i
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
            "artifact_id": artifact_id,
            "bbox": bbox,
            # Page panels get a guaranteed page scope (matching is page-scoped); spreads are matched
            # by page_range, not page_number, so leave theirs as carried.
            "page_number": (entry.get("page_number") if is_spread
                            else _derive_page_number(artifact_id, entry.get("page_number"))),
            "coordinate_space": "spread" if is_spread else (
                entry.get("coordinate_space") if isinstance(entry, dict) else None),
            "flags": flags,
            "page_range": page_range,
            "order": order_of.get(artifact_id),   # human-approved reading position within the page
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


# Metadata content-schema versions Scout can parse. Fail-fast on anything else so an unknown structure is
# never silently mis-extracted. (Version SKEW between the two sides is still handled downstream as
# unsupported_schema; this only gates versions we don't know how to read at all.)
# Includes the pre-`v1.1` literal `"v1"` (routes to the v1.1 four-field extractor, matching pre-adapter-v3
# behavior when there was no version gate) so a historical review record still audits rather than fail-fasting.
SUPPORTED_METADATA_VERSIONS = ("v1", "v1.1", "v2")

# Panel Intelligence v2 content leaves under `output.*`. The LLM-editorial leaves are compared; any leaf the
# Publisher marks non-`llm` in `field_sources` (e.g. computed `classification.colors`) is routed out of the
# compared set and recorded as a hash only. `V2_KNOWN_NON_LLM` is a defensive default so the one field we
# KNOW is deterministic is excluded even if a `field_sources` entry is ever omitted.
V2_CONTENT_LEAVES = ("entities.characters", "entities.objects", "entities.environment",
                     "narrative.summary", "narrative.dialogue",
                     "classification.shot_type", "classification.colors",
                     "classification.tags.mood", "classification.tags.action",
                     "classification.tags.weather", "classification.tags.time_of_day")
V2_KNOWN_NON_LLM = frozenset({"classification.colors"})


def _get_path(obj, dotted):
    """Read a dotted path from a nested dict; ``None`` if any segment is missing/not a dict."""
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _extract_v2(output_obj, field_sources):
    """Split the v2 `output.*` leaves into (editorial, non_editorial) using the Publisher `field_sources`
    marker: a leaf is compared iff its source is ``llm`` (the default for any unlisted field). Non-`llm`
    leaves (e.g. computed `colors`) are recorded but never compared. Deterministic; future computed/publisher
    fields self-exclude via their marker."""
    o = output_obj if isinstance(output_obj, dict) else {}
    fs = field_sources if isinstance(field_sources, dict) else {}
    editorial, non_editorial = {}, {}
    for leaf in V2_CONTENT_LEAVES:
        val = _get_path(o, leaf)
        # A KNOWN-deterministic leaf (colors) is ALWAYS non-editorial — a mislabeled `field_sources` marker
        # must never pull a computed field into the compared set (it would always read "accepted" and
        # inflate). Every other leaf trusts the marker, defaulting to `llm` (compared) when unlisted.
        if leaf in V2_KNOWN_NON_LLM:
            source = "computed"
        else:
            source = fs.get("output." + leaf, "llm")
        (editorial if source == "llm" else non_editorial)[leaf] = val
    return editorial, non_editorial


def _extract_grounding(context_source):
    """The SUPPORTING-MATERIAL grounding entries from a per-output ``context_source`` (CBI-2b) — the
    approved materials + revisions the output grounded on. Filters to ``kind == "supporting_material"``
    (registry grounding rides the same list as ``kind: "registry_entity"`` and is not materials). Returns
    a deterministically-sorted list of ``{material_id, category, subtype, edition_id, files:[{file_id,
    revision}]}`` — identifiers only (references, never raw material text). Empty when grounding is off /
    absent (byte-identical baseline)."""
    if not isinstance(context_source, list):
        return []
    out = []
    for e in context_source:
        if not isinstance(e, dict) or e.get("kind") != "supporting_material":
            continue
        files = e.get("files") if isinstance(e.get("files"), list) else []
        norm_files = sorted(
            ({"file_id": f.get("file_id"), "revision": f.get("revision")}
             for f in files if isinstance(f, dict)),
            key=lambda f: (str(f["file_id"]), str(f["revision"])))
        out.append({"material_id": e.get("material_id"), "category": e.get("category"),
                    "subtype": e.get("subtype"), "edition_id": e.get("edition_id"),
                    "files": norm_files})
    return sorted(out, key=lambda m: str(m["material_id"]))


def _normalize_metadata(metadata_obj, side):
    """Normalize a ``{llm_enrichment_output_version, llm_enrichment_outputs:[...]}`` object into Scout's
    canonical ``{artifact_id: {schema_version, fields, non_editorial, provenance...}}`` map. ``fields`` is
    the LLM-editorial content leaves the delta compares — the four v1.1 fields, or the Panel Intelligence
    v2 per-leaf set (marker-filtered). The schema version is carried so the delta can enforce
    schema-version scoping. Extraction routes by version prefix (v2 shape vs the v1.1 four fields); the
    version GATE (fail-fast when BOTH sides share an unknown version) lives in ``adapt_review`` where both
    sides are visible — a one-sided unknown version is a skew and abstains downstream, not a raise."""
    if not isinstance(metadata_obj, dict):
        raise ReviewContractError(f"{side} metadata must be a JSON object")
    schema_version = metadata_obj.get("llm_enrichment_output_version")
    outputs = metadata_obj.get("llm_enrichment_outputs", [])
    if not isinstance(outputs, list):
        raise ReviewContractError(f"{side} metadata.llm_enrichment_outputs must be a list")
    is_v2 = str(schema_version).startswith("v2")
    canon = {}
    for i, out in enumerate(outputs):
        src = f"{side} metadata.llm_enrichment_outputs[{i}]"
        artifact_id = _require(out, "artifact_id", src)
        gp = out.get("generation_provenance")
        if is_v2:
            fields, non_editorial = _extract_v2(out.get("output"), out.get("field_sources"))
        else:
            fields, non_editorial = _extract_content_fields(out.get("output")), {}
        # `publisher_notes` is a record-level sibling (never LLM) — recorded, never compared, hash-only.
        if out.get("publisher_notes") is not None:
            non_editorial["publisher_notes"] = out.get("publisher_notes")
        canon[artifact_id] = {
            "schema_version": schema_version,
            "fields": fields,
            # Non-editorial content (computed/publisher) — recorded downstream as a HASH only, never
            # compared and never persisted as raw text.
            "non_editorial": non_editorial,
            # Publisher-emitted provenance facts (P1), siblings of `output` and additive. `generation_provenance`
            # carries identifiers/hashes only; `generation_disposition` is the fresh|preserved_* flag;
            # `generation_count` is the per-panel recall counter (best-effort — v2 recall endpoint).
            "generation_provenance": gp if isinstance(gp, dict) else None,
            "generation_disposition": out.get("metadata_generation_provenance"),
            "generation_count": (gp.get("generation_count") if isinstance(gp, dict) else None),
            # CBI-2b materials grounding (which approved materials+revisions this output grounded on),
            # from the per-output context_source — the AUTHORITATIVE source (not the run-level pin).
            "grounding": _extract_grounding(out.get("context_source")),
        }
    return canon


def _generated_summary(generated_panel_geometry):
    """The generated side's page/panel totals (for per-page benchmark denominators). Best-effort:
    missing fields are ``None``, never fabricated."""
    g = generated_panel_geometry if isinstance(generated_panel_geometry, dict) else {}
    return {"total_pages": g.get("total_pages"),
            "total_story_pages": g.get("total_story_pages"),
            "total_panels": g.get("total_panels")}


def _fresh_generation_provenance(generated_metadata):
    """Report-level generator identity derived from the per-output ``generation_provenance`` of the
    FRESH generated outputs (Publisher enhancement #1). Preserved outputs keep a *prior* run's
    provenance, so they are excluded — the comparability axis must reflect the generator that produced
    THIS run's fresh output. When the fresh outputs disagree on a value it becomes a DETERMINISTIC
    ``mixed:<hash-of-the-distinct-values>`` marker (not ``None``) and ``heterogeneous`` is set — so two
    reports with *different* mixes get *different* comparability keys and are never silently joined into
    one series, while a single mix stays stable. Returns ``None`` values when the per-output provenance is
    absent (legacy pre-provenance revisions)."""
    gm = generated_metadata if isinstance(generated_metadata, dict) else {}
    outputs = gm.get("llm_enrichment_outputs")
    fresh = []
    if isinstance(outputs, list):
        for out in outputs:
            if not isinstance(out, dict):
                continue
            gp = out.get("generation_provenance")
            if out.get("metadata_generation_provenance") == "fresh" and isinstance(gp, dict):
                fresh.append(gp)

    def agree(key):
        vals = sorted({str(gp.get(key)) for gp in fresh if gp.get(key) not in (None, "")})
        if len(vals) == 0:
            return None, False                    # absent
        if len(vals) == 1:
            return vals[0], False                 # agreed
        # heterogeneous -> a stable marker keyed on the exact distinct set (mix-distinct, never collapsed).
        digest = hashlib.sha256("|".join(vals).encode("utf-8")).hexdigest()[:12]
        return f"mixed:{digest}", True

    model, m_h = agree("model")
    prompt_version, pv_h = agree("prompt_version")
    prompt_sha256, ps_h = agree("prompt_sha256")
    return {
        "model": model, "prompt_version": prompt_version, "prompt_sha256": prompt_sha256,
        "fresh_output_count": len(fresh),
        "heterogeneous": bool(m_h or pv_h or ps_h),
    }


def _metadata_provenance(generated_metadata, approved_metadata):
    """Metadata generation provenance for the comparability contract — enrichment schema versions
    on both sides, plus the generator identity (model / prompt_version / prompt_sha256) the Publisher
    now emits per output (enhancement #1). The identity is taken from the FRESH outputs
    (``_fresh_generation_provenance``); a legacy top-level probe remains as a fallback so
    pre-provenance revisions still parse (they yield ``None`` exactly as before).

    Security: only identifiers/versions/hashes are captured — never prompt bodies, secrets, or credentials.
    """
    gm = generated_metadata if isinstance(generated_metadata, dict) else {}
    am = approved_metadata if isinstance(approved_metadata, dict) else {}
    # Legacy top-level probe (pre-#1 emitters / absent -> None).
    def pick(obj, *names):
        for n in names:
            if isinstance(obj, dict) and obj.get(n) not in (None, ""):
                return obj[n]
        return None
    fresh = _fresh_generation_provenance(generated_metadata)
    return {
        "generated_schema_version": gm.get("llm_enrichment_output_version"),
        "approved_schema_version": am.get("llm_enrichment_output_version"),
        "prompt_id": pick(gm, "prompt_id", "enrichment_prompt_id"),
        "prompt_version": fresh["prompt_version"] or pick(gm, "prompt_version", "enrichment_prompt_version"),
        "model": fresh["model"] or pick(gm, "model", "enrichment_model", "llm_model"),
        "prompt_sha256": fresh["prompt_sha256"],
        "provider": pick(gm, "provider", "model_provider", "llm_provider"),
        # Where the identity came from + whether the fresh outputs agreed (surfaced, not hidden).
        "provenance_source": "per_output_fresh" if fresh["fresh_output_count"] else "legacy_or_absent",
        "provenance_heterogeneous": fresh["heterogeneous"],
        "fresh_output_count": fresh["fresh_output_count"],
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
        # Fail-fast ONLY when both sides share an UNSUPPORTED metadata version — a genuine unknown
        # structure we must not mis-extract (the Publisher's version-bump protocol means this shouldn't
        # happen un-negotiated). A version SKEW (the two sides differ) is NOT a hard failure — it abstains
        # downstream as unsupported_schema (a WARNING), preserving graceful handling of an old/mismatched side.
        gen_ver = (gen_meta_raw or {}).get("llm_enrichment_output_version")
        app_ver = (review_report.get("approved_metadata") or {}).get("llm_enrichment_output_version")
        if gen_ver == app_ver and gen_ver not in SUPPORTED_METADATA_VERSIONS:
            raise ReviewContractError(
                f"both sides carry unsupported metadata llm_enrichment_output_version {gen_ver!r} "
                f"(supported: {', '.join(SUPPORTED_METADATA_VERSIONS)}; review_id={review_id}) — "
                "refusing to extract an unknown structure")
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
        # CBI-2b run-level VERSION PIN (materials_grounding_version + resolution_contract_version) from each
        # side's top-level metadata doc — a version stamp only, NOT the material list. None when grounding
        # off (byte-identical baseline). The authoritative grounding is per-artifact `grounding` above.
        "materials_grounding_pin": {
            "generated": (review_report.get("generated_metadata") or {}).get("materials_grounding"),
            "approved": (review_report.get("approved_metadata") or {}).get("materials_grounding"),
        },
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
