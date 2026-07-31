# Certification Report — Metadata Accuracy v2 (Publisher→Scout metadata-provenance interface)

**Track:** Week 11 · Metadata Provenance Interface
**Branch:** `week11-metadata-provenance-v2`
**Date:** 2026-07-31
**Discipline:** certified-first (build → adversarial review → certify → deploy → activate/live-cert, each separate)
**Status:** CODE-COMPLETE · adversarially reviewed · offline-certified · HELD for deploy + coordinated live cert

---

## 1. What changed and why

The Publisher shipped (`edenseek-publishing` commit `5da0532`, its own Gate-B hostile review passed) two
**additive, Publisher-emitted provenance facts** on every generated metadata output — siblings of the
`output` subtree, **no content-schema change**, `llm_enrichment_output_version` stays `v1.1`:

1. **`generation_provenance`** `{model, prompt_version, prompt_sha256, temperature, mode}` — the generator
   identity, per output. A *preserved* output keeps the provenance of the run that actually generated it.
2. **`metadata_generation_provenance`** `"fresh" | "preserved_approved" | "preserved_prior_success"` — the
   per-artifact disposition. `fresh` is this run's raw first-pass LLM output (the true "before" state);
   the two `preserved_*` values equal prior approved content by construction.

Scout consumes them to (a) fill the previously-null `metadata_model` / `metadata_prompt_version`
comparability axes and add a `metadata_prompt_sha256` axis, and (b) measure acceptance over **fresh outputs
only**, excluding preserved outputs from the denominator. This closes the robustness caveat the Publisher
raised: the metric no longer rests on the invisible generate-before-approve invariant — it reads an emitted
flag.

This is a **metadata *interface* evolution**, not a content or workflow change. It does not alter editorial
behavior, approved-dataset semantics, or Publisher authority; Scout remains an independent read-only auditor.

## 2. Emitted field contract (authoritative — as consumed by Scout)

Per entry of `review_report.json → generated_metadata.llm_enrichment_outputs[]`, sibling of `output`:

| Field | Shape | Meaning | Scout use |
|---|---|---|---|
| `generation_provenance.model` | str | `OPENAI_MODEL` at generation | `metadata_model` axis (from fresh) |
| `generation_provenance.prompt_version` | str | human-label prompt version | `metadata_prompt_version` axis (from fresh) |
| `generation_provenance.prompt_sha256` | str | hash of the 4 prompt templates | `metadata_prompt_sha256` axis (from fresh) |
| `generation_provenance.temperature` | num | sampling temp | carried in provenance (not an axis) |
| `generation_provenance.mode` | `text`\|`vision` | whether a panel image was sent | carried in provenance (not an axis) |
| `metadata_generation_provenance` | `fresh`\|`preserved_approved`\|`preserved_prior_success` | per-artifact disposition | acceptance-denominator filter |

Invariants relied on: both keys are **additive siblings** of `output`; compared `output.*` content and
`llm_enrichment_output_version` are **unchanged**; existing certified revisions (incl. `rev_0be8dc34`) carry
**neither** field. These are provenance facts (Principle P1) — Publisher emits, Scout derives.

## 3. Scout-side changes (this branch)

- **`review_contract_adapter.py`**
  - `_normalize_metadata`: carries `generation_provenance` (dict|None) and `generation_disposition`
    (the flag) per artifact into the canonical map. Reads only known keys → **tolerates** the new siblings
    with no fail-fast (regression-tested).
  - `_fresh_generation_provenance` (new): aggregates report-level `model`/`prompt_version`/`prompt_sha256`
    from the **fresh** outputs only. Disagreement across fresh outputs → value `None` +
    `heterogeneous: true` (surfaced, never silently collapsed). Absent → `None`.
  - `_metadata_provenance`: now sources the identity from `_fresh_generation_provenance`, with the legacy
    top-level probe kept as a fallback so pre-provenance revisions parse exactly as before. Adds
    `prompt_sha256`, `provenance_source` (`per_output_fresh`|`legacy_or_absent`), `provenance_heterogeneous`,
    `fresh_output_count`.
- **`delta_metadata_revision.py`**
  - `METADATA_ACCURACY_VERSION` `v1 → v2`.
  - Each revision-distance record now carries `generated_disposition`.
  - `_metadata_accuracy` rewritten to compute acceptance over **fresh** records only (self-contained over
    `records`); preserved outputs excluded from the denominator and per-field burden. Adds
    `denominator_basis`, `excluded_preserved_field_count`, `excluded_preserved_artifacts`, and
    `disposition_coverage` (`none`|`all`|`partial`) — the last surfaces a contract-violating partial
    emission instead of silently trusting the backward-compat default.
  - The surfaced `global`/`per_field` are now the **fresh-only** aggregates (the certified surface every
    consumer reads); the all-common revision-distance record is retained beside them as
    `global_all_common`/`per_field_all_common` (`METADATA_REVISION_DISTANCE_VERSION` still `v1`,
    descriptive/audit only). On all-fresh data the two are identical.
- **`scout_report_index.py`**: `metadata_prompt_sha256` added to `METADATA_AXES` and read in `metadata_axes`.
- **Docs**: `docs/architecture/SCOUT_REPORT_INDEX.md` axis list updated (no drift).

## 4. Backward compatibility (proven)

Absent disposition is treated as **fresh**, so on all-fresh / no-flag data v2 is **numerically identical**
to v1. Legacy revisions with neither field parse unchanged and yield `null` provenance +
`disposition_coverage: none`. Regression tests assert:
- `test_v2_all_fresh_equals_legacy_number` — explicit-all-fresh acceptance == no-flags acceptance.
- `test_metadata_accuracy_v2` — v2 acceptance numerator/denominator == the global accepted/comparable on the
  legacy fixture (0 excluded).
- `test_legacy_revision_yields_null_provenance` — no provenance emitted → all axis values `None`,
  `provenance_source: legacy_or_absent`.

**Implication for `rev_0be8dc34`:** a v2 re-audit of the certified live revision (which has neither field)
reproduces the same **96.4%** acceptance — verified offline via the identical-fixture property; to be
re-confirmed live during the coordinated cert.

## 5. Version / comparability / idempotency

- `metadata_accuracy_version` is in **both** the comparability axis (`metadata_axes`) **and** the ledger
  fingerprint (`scout_delta_audit.static_versions()`). v1→v2 therefore (a) changes the fingerprint → the
  re-audit **runs** (no skip), and (b) changes the `metadata_comparability_key` → the `run_id` changes →
  **no collision** with the existing v1 metadata run. This is the exact dual-condition from the prior
  reconciliation lesson, satisfied by construction.
- Adding `metadata_prompt_sha256` to the axis is intended: it makes v1 and v2 series (and any silent prompt
  change) a visible methodology boundary rather than a silent splice.
- **Version-semantics note:** the surfaced `global`/`per_field` became fresh-only while
  `METADATA_REVISION_DISTANCE_VERSION` stays `v1`. This is safe — that version stamps the
  thresholds/weights/distance-definition (all unchanged), the aggregate-population change is a **no-op on
  any revision lacking provenance flags** (all legacy data + `rev_0be8dc34` + an all-fresh live-cert), and
  any revision carrying preserved outputs is already separated by `metadata_accuracy_version=v2` in **both**
  the comparability axis and the ledger fingerprint. No historical series is silently re-scored.

## 6. Tests

Full suite: **353 passed**. New/updated (in `tests/test_metadata_revision.py`, `tests/_delta_fixtures.py`):
adapter tolerates+reads siblings; provenance identity from fresh; legacy→null; heterogeneous surfaced;
preserved provenance ignored for axis; `metadata_prompt_sha256` axis wired; preserved excluded from
denominator (exact numerator/denominator deltas); `preserved_prior_success` excluded; v2==legacy on
all-fresh; `disposition_coverage` none/all/partial.

## 7. Adversarial review (two rounds, independent)

**Round 1** found 4 issues; **Round 2** verified the fixes and found that #1 was only partially closed (a
second inflated surface), plus 3 low-priority edges. All are now resolved:

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MAJOR | Headline (and, on re-review, `body["metadata_benchmark"]` → index → Metadata Intelligence trend) still sourced acceptance/edit/distance rates from the all-common `global`, contradicting the fresh-only `metadata_accuracy` whenever a preserved output exists. | `benchmark_headline` now sources every rate from the fresh aggregate; and `compute_metadata_benchmark` now **exposes `global`/`per_field` as the fresh-only aggregates** (all-common retained as `global_all_common`/`per_field_all_common`), so every consumer — report body, index entry, `scout_intelligence`, `scout_benchmark` — reads fresh-only. Runtime-verified consistent (0.4/5 across all surfaces); all-common (9) retained for audit. |
| 2 | MAJOR | `partial` disposition coverage silently re-inflated the rate and still emitted a trustworthy `meets_target`. | `provisional=true` + `meets_target=None` on partial; surfaced in the headline (`metadata_accuracy_provisional`, `disposition_coverage`). |
| 3/4 | MINOR/NIT | Heterogeneous fresh provenance collapsed the axis to `None`, so different mixes shared a key; legacy fallback could override the intentional `None`. | Deterministic `mixed:<sha256>` marker per distinct mix → distinct keys, never silently joined; marker is truthy so fallback can't override. |
| B | MINOR | Zero-fresh (all-preserved) revision read as `meets_target=False` / "0% accepted". | `meets_target=None` when `comparable==0`. |
| C | NIT | `corrections_per_artifact` artifact-count basis differed between fresh and all-common. | `fresh_comparable_artifacts` counts fresh **schema-matched** artifacts, mirroring `comparable_artifacts`. |
| D | NIT | `disposition_coverage` computed over scored records only → all-abstention-but-flagged read "none". | Coverage computed over **all** records (the flag is per-artifact). |

Claims the reviewers tried and could not break: backward-identical on legacy/all-fresh; fresh-only
denominator; preserved never counted; determinism; no raw text; `run_id`/comparability boundary correct;
no downstream consumer assumes `meets_target` is a bool.

## 8. Scope boundary / documented follow-ups

- **`scout_intelligence.py` (Metadata Intelligence projection)** — now **reads the fresh-only surface**
  automatically (it consumes `metadata_benchmark.global`/`per_field`, which are fresh as of the §7-#1 fix).
  No longer a follow-up; correct on mixed-flow data too.
- **Dashboard surfacing** of `denominator_basis` / `excluded_preserved_*` / `disposition_coverage` /
  `provisional` is deferred to our joint UI review (today they'd read `none` / 0 / not-provisional on the
  live-cert revision). The dashboard reads only the fresh-only `metadata_accuracy` and never `meets_target`,
  so nothing is misrendered; one stale `v1→v2` label was corrected.
- **Per-leaf-field granularity** refinement lands with the future structural form change + `v2` field
  contract (separate coordinated increment), not here.

## 9. Certification statement

The change is additive and backward-compatible, deterministic, stores references+hashes only, preserves
Publisher authority and Scout's read-only boundary, and clearly communicates a metadata **interface**
evolution (`METADATA_ACCURACY_VERSION v2` + `metadata_prompt_sha256` axis) rather than a content/workflow
change. **Offline-certified.** Remaining gates: deploy (SCOUT_RUNTIME_MODE=production), then the coordinated
live certification against a fresh Publisher-generated issue carrying the provenance fields.
