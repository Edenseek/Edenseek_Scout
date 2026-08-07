"""Track A — deterministic RESOLVED-GRAPH material auditor (Scout).

Scout's INDEPENDENT mirror of the Publisher's certified Supporting-Materials resolution contract. It walks
the per-scope Material Indexes (issue → series → title_group → publisher), applies the ordered filters of the
versioned resolution contract, and produces the effective approved-material set for a target — then
**cross-checks that set against the Publisher's own emitted `resolved_materials.json`.** Two independent
implementations agreeing is the certification; a divergence is a finding on one side (Principle P1/P2).

Boundary: Scout MIRRORS, never IMPORTS, the Publisher resolver (ADR-0001 — Scout is a separate deployed
service). The mirror is PINNED to ``resolution_contract_version``; it fail-fasts on an unknown version rather
than reinterpret a changed order. Read-and-advise: it emits findings, never mutates.

The resolution contract (v1, corrected order) — `retirement_exclusion` + `edition_filter` are per-record
ELIGIBILITY gates applied DURING the inheritance union (BEFORE cross-record supersession), so an ineligible
record never suppresses; `rank_aware_explicit_supersession` then removes explicitly-superseded materials;
`lifecycle_publisher_approved_only` is the TERMINAL filter (the Publisher's `context_builder_view`).

Governance: identifiers/references only (material_id / file_id / revision) — never material file bytes/text.
Offline (Phase A): consumes parsed dicts; the S3 read of the indexes + `resolved_materials.json` is Phase B.
"""

RESOLUTION_MIRROR_VERSION = "v1"
SUPPORTED_RESOLUTION_CONTRACT_VERSIONS = ("v1",)

# Most-specific → least-specific. Lower rank = narrower scope (wins an inheritance collision).
_SCOPE_RANK = {"issue": 0, "series": 1, "title_group": 2, "publisher": 3}


def _records(index):
    """Records list from one per-scope Material Index, tolerant of the wrapper key (``records`` /
    ``materials`` / ``entries``). Non-dict / missing → empty."""
    if not isinstance(index, dict):
        return []
    for key in ("records", "materials", "entries"):
        v = index.get(key)
        if isinstance(v, list):
            return [r for r in v if isinstance(r, dict)]
    return []


def _rank(record):
    return _SCOPE_RANK.get((record.get("scope") or {}).get("level"), 99)


def _sorted_files(pairs):
    """Deterministically sort (file_id, revision) pairs with a TOTAL order that tolerates None (a missing
    file_id/revision must surface as a finding via a key mismatch, never crash the audit on a mixed-None sort)."""
    return tuple(sorted(pairs, key=lambda t: (t[0] is None, str(t[0]), t[1] is None, str(t[1]))))


def _material_key(record):
    """A material's identity for the effective-set comparison: (material_id, sorted (file_id, revision)
    tuples). References only. The record shape carries the file revision under ``artifact_ref.revision``."""
    files = _sorted_files((f.get("file_id"), (f.get("artifact_ref") or {}).get("revision") or f.get("revision"))
                          for f in (record.get("files") or []) if isinstance(f, dict))
    return (record.get("material_id"), files)


def _resolved_key(entry):
    """Same identity shape for a Publisher `resolved_materials.resolved` entry (which carries flat
    `files:[{file_id, revision}]`)."""
    files = _sorted_files((f.get("file_id"), f.get("revision"))
                          for f in (entry.get("files") or []) if isinstance(f, dict))
    return (entry.get("material_id"), files)


def resolve_effective_materials(records, target_edition_id=None):
    """Scout's mirror of the certified v1 cascade → the effective approved-material set for the target.

    records: a flat list of Material records across ALL scope levels (each carries scope.level). Order of the
    filters follows the contract's stated semantic (eligibility-during-union, then supersession, then
    approved-only terminal). Returns the list of effective records (approved-only), deterministically ordered."""
    # 1 + 2 — per-record ELIGIBILITY gates, applied DURING the union (before supersession):
    #   retirement_exclusion: a retired record is ineligible.
    #   edition_filter: an edition-bound record (scope.edition_id set) is eligible ONLY for its edition;
    #                   an edition-agnostic record (no edition_id) is always eligible.
    eligible = []
    for r in records:
        if r.get("status") == "retired":
            continue
        ed = (r.get("scope") or {}).get("edition_id")
        if ed is not None and ed != target_edition_id:
            continue
        eligible.append(r)

    # 3 — inheritance union, supplement-by-default, MOST-SPECIFIC kept on a material_id collision.
    by_id = {}
    for r in eligible:
        mid = r.get("material_id")
        if mid not in by_id or _rank(r) < _rank(by_id[mid]):
            by_id[mid] = r

    # 4 — rank_aware_explicit_supersession (Publisher-confirmed authoritative semantic,
    # material_index_merge.resolve_effective_materials):
    #   * A surviving record R suppresses target T named in R.supersedes IFF rank(T) > rank(R) — T is at a
    #     STRICTLY LESS-SPECIFIC scope than R. Broader can't suppress narrower; same-scope is a no-op
    #     (within-scope replacement is expressed by the `superseded` lifecycle status, not the cascade edge).
    #   * Only SURVIVING (kept, not-yet-suppressed) records suppress — a suppressed record does NOT apply its
    #     own edges (so chains resolve correctly).
    #   * Collision-shadowed records are already dropped (not in `by_id`), so their edges never apply.
    #   * Evaluated MOST-SPECIFIC-FIRST (material_id tiebreak) — a determinism/order-independence device (a
    #     record that could suppress R is more specific than R, hence processed first).
    survivors_ordered = sorted(by_id.values(), key=lambda r: (_rank(r), str(r.get("material_id"))))
    suppressed = set()
    for r in survivors_ordered:
        rid = r.get("material_id")
        if rid in suppressed:
            continue                                   # a suppressed record does not suppress others
        r_rank = _rank(r)
        for rel in (r.get("relationships") or []):
            if rel.get("rel") == "supersedes":
                tgt_obj = rel.get("target") or {}
                # The Publisher resolver applies a supersedes edge only when it is BOUND
                # (material_index.py::supersedes_ids). On valid data bound<=>id-present, but mirror the
                # actual check: an explicitly-unbound edge never suppresses (bound or absent -> id-presence).
                if tgt_obj.get("binding_status") not in (None, "bound"):
                    continue
                tgt = tgt_obj.get("id")
                if tgt is not None and tgt in by_id and _rank(by_id[tgt]) > r_rank:
                    suppressed.add(tgt)                 # strictly-less-specific target only
    survivors = [r for mid, r in by_id.items() if mid not in suppressed]

    # 5 — lifecycle_publisher_approved_only (TERMINAL — the Publisher's context_builder_view).
    effective = [r for r in survivors if r.get("status") == "publisher_approved"]
    return sorted(effective, key=lambda r: str(r.get("material_id")))


def _authoring_findings(records):
    """Authoring-layer invariant checks over the raw records (identifiers only). Findings are advisory
    observations, never mutations. Facts (the records) are the Publisher's; these are Scout's derived
    observations about their internal consistency."""
    findings = []
    ids = {r.get("material_id") for r in records}

    # (0) A material_id authored at MORE THAN ONE scope. The store enforces single placement (authored once,
    # never duplicated at descendants), so a cross-scope collision is an authoring anomaly — and it is exactly
    # the case where the resolved layer drops the shadowed record's edge, so surface it explicitly.
    scopes_by_id = {}
    for r in records:
        scopes_by_id.setdefault(r.get("material_id"), set()).add((r.get("scope") or {}).get("level"))
    for mid, levels in sorted(scopes_by_id.items(), key=lambda kv: str(kv[0])):
        if len(levels) > 1:
            findings.append({"code": "materials.cross_scope_collision", "severity": "WARNING",
                             "material_id": mid, "scope_levels": sorted(levels, key=str),
                             "detail": "same material_id authored at more than one scope (single-placement violation)"})

    # (a) Every `supersedes` target must resolve to a known material (no dangling supersession edge).
    for r in records:
        for rel in (r.get("relationships") or []):
            if rel.get("rel") == "supersedes":
                tgt = (rel.get("target") or {}).get("id")
                if tgt is not None and tgt not in ids:
                    findings.append({"code": "materials.dangling_supersedes", "severity": "WARNING",
                                     "material_id": r.get("material_id"), "target": tgt,
                                     "detail": "supersedes target is not a known material"})

    # (b) One active `publisher_approved` per supersession lineage. Build lineages by union-find over the
    # supersedes edges, then flag any lineage with >1 approved record.
    parent = {mid: mid for mid in ids}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for r in records:
        for rel in (r.get("relationships") or []):
            if rel.get("rel") == "supersedes":
                tgt = (rel.get("target") or {}).get("id")
                if tgt in ids:
                    union(r.get("material_id"), tgt)
    approved_by_lineage = {}
    for r in records:
        if r.get("status") == "publisher_approved":
            approved_by_lineage.setdefault(find(r.get("material_id")), []).append(r.get("material_id"))
    for lineage, approved in sorted(approved_by_lineage.items(), key=lambda kv: str(kv[0])):
        if len(approved) > 1:
            findings.append({"code": "materials.multiple_active_approved", "severity": "FAIL",
                             "lineage": lineage, "material_ids": sorted(approved, key=str),
                             "detail": "more than one publisher_approved record in one supersession lineage"})

    # (c) A record that is a supersedes TARGET should not still be publisher_approved (should be superseded).
    superseded_targets = {(rel.get("target") or {}).get("id")
                          for r in records for rel in (r.get("relationships") or [])
                          if rel.get("rel") == "supersedes"}
    for r in records:
        if r.get("material_id") in superseded_targets and r.get("status") == "publisher_approved":
            findings.append({"code": "materials.superseded_still_approved", "severity": "WARNING",
                             "material_id": r.get("material_id"),
                             "detail": "record is superseded by another but still marked publisher_approved"})
    return findings


def compute_resolution_audit(scope_indexes, resolved_materials, resolution_contract, target_edition_id=None):
    """The Track-A resolved-graph audit for one target.

    ``scope_indexes``: ``{scope_level: material_index_dict}`` (issue/series/title_group/publisher).
    ``resolved_materials``: the Publisher's emitted `resolved_materials.json` (the diff target).
    ``resolution_contract``: the `registry/resolution_contract.json` manifest (for the version pin).
    Returns a report: the cross-check (Scout mirror vs Publisher resolved) + authoring findings, or
    NOT-APPLICABLE on an unknown/absent contract version (Scout fail-fasts rather than reinterpret)."""
    contract = resolution_contract if isinstance(resolution_contract, dict) else {}
    cver = contract.get("resolution_contract_version")
    if cver not in SUPPORTED_RESOLUTION_CONTRACT_VERSIONS:
        return {"applicable": False, "reason": "unsupported_resolution_contract_version",
                "resolution_contract_version": cver, "version": RESOLUTION_MIRROR_VERSION}

    all_records = [r for lvl in ("issue", "series", "title_group", "publisher")
                   for r in _records((scope_indexes or {}).get(lvl))]

    rm = resolved_materials if isinstance(resolved_materials, dict) else {}
    # A version SKEW between the manifest and the Publisher's resolved snapshot -> abstain the cross-check
    # (measure against a single consistent contract version, never a wrong divergence).
    rm_cver = rm.get("resolution_contract_version")
    version_skew = rm_cver is not None and rm_cver != cver

    mirror = resolve_effective_materials(all_records, target_edition_id=target_edition_id)
    publisher_resolved = rm.get("resolved") if isinstance(rm.get("resolved"), list) else []

    mine = {_material_key(r) for r in mirror}
    theirs = {_resolved_key(e) for e in publisher_resolved if isinstance(e, dict)}
    mine_ids = {k[0] for k in mine}
    theirs_ids = {k[0] for k in theirs}
    # Deterministic id->files maps. ALL material_id sorts use a None-safe key (`_kid`) — a missing
    # material_id must surface as a divergence, never crash the audit on a mixed None/str sort.
    def _kid(k):
        return (str(k[0]), str(k[1]))
    mine_by_id = {k[0]: k[1] for k in sorted(mine, key=_kid)}
    theirs_by_id = {k[0]: k[1] for k in sorted(theirs, key=_kid)}
    # Flag (never silently dedup) a material_id appearing twice in the Publisher's resolved list.
    resolved_id_list = [e.get("material_id") for e in publisher_resolved if isinstance(e, dict)]
    duplicate_resolved_ids = sorted({m for m in resolved_id_list if resolved_id_list.count(m) > 1}, key=str)

    if version_skew:
        # Abstain: a cross-version comparison is meaningless — report no divergence lists, only the skew.
        agree_ids = only_scout = only_publisher = file_mismatches = []
    else:
        agree_ids = sorted(mine_ids & theirs_ids, key=str)
        only_scout = sorted(mine_ids - theirs_ids, key=str)
        only_publisher = sorted(theirs_ids - mine_ids, key=str)
        file_mismatches = sorted((mid for mid in agree_ids if mine_by_id[mid] != theirs_by_id[mid]), key=str)
    matches = (not version_skew and not only_scout and not only_publisher
               and not file_mismatches and not duplicate_resolved_ids)

    return {
        "applicable": True,
        "version": RESOLUTION_MIRROR_VERSION,
        "resolution_contract_version": cver,
        "resolved_materials_version": rm.get("resolved_materials_version"),
        "version_skew": version_skew,
        # Publisher-confirmed: a record suppresses a target only if strictly more specific (rank(T)>rank(R)),
        # from surviving non-suppressed records, never from a collision-shadowed record.
        "supersession_semantic": "rank_aware_strict_more_specific",
        "target": rm.get("target"),
        "target_edition_id": target_edition_id,
        "records_total": len(all_records),
        "cross_check": {
            "matches": matches,
            "scout_effective_count": len(mine_ids),
            "publisher_resolved_count": len(theirs_ids),
            "agree": agree_ids,
            "only_scout": only_scout,             # Scout resolved it, Publisher didn't -> investigate
            "only_publisher": only_publisher,     # Publisher resolved it, Scout didn't -> investigate
            "file_revision_mismatches": file_mismatches,
            "duplicate_resolved_ids": duplicate_resolved_ids,
        },
        "authoring_findings": _authoring_findings(all_records),
    }
