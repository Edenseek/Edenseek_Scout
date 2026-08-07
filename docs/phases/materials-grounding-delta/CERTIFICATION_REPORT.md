# Certification Report — Materials-Grounding Delta (CBI-2b build "B")

**Track:** Week 12 · Supporting Materials · **Branch:** `week12-materials-grounding-delta`
**Date:** 2026-08-06 · **Discipline:** certified-first (build → 2 adversarial rounds → certify → deploy → live cert)
**Status:** CODE-COMPLETE · adversarially reviewed (2 rounds, all findings resolved) · offline-certified · HELD
for merge + live cert against real `EDENSEEK_MATERIALS_GROUNDING=on` data.

## 1. What it is
The generated-vs-approved **materials-grounding** audit: for each generated LLM output, compare *which approved
Supporting Materials it grounded on* (generated side vs approved side). The materials analogue of the metadata
revision-distance benchmark — it answers "did the human have to re-ground outputs the LLM grounded wrong?"
Advisory only (Charter §4); Scout measures, the Publisher certifies.

## 2. Contract consumed (Johnny's certified CBI-2b, corrected shape)
- **Authoritative per-output source:** `output.context_source` entries with `kind == "supporting_material"`
  (`material_id, category, subtype, edition_id, files:[{file_id, revision}]`). Registry-entity and other
  kinds are ignored (filtered by `kind`).
- **Run-level `materials_grounding` pin** (`materials_grounding_version`, `resolution_contract_version`) is a
  **version stamp only** — never the material list, never authoritative over `context_source`. The audit is
  driven off per-output `context_source`; the pin only stamps/boundaries the contract versions.
- **Off-by-default:** grounding off → neither the entries nor the pin appear → the benchmark is
  **NOT-APPLICABLE** (`reason: "no_materials_grounding"`), a byte-identical baseline, never a failure.

## 3. Scout-side changes (additive)
- **`review_contract_adapter.py`** — `_extract_grounding(context_source)` (kind-filtered, id-less entries
  dropped, files + entries deterministically sorted, identifiers only); per-output `grounding` carried on
  each canonical metadata entry; the run-level pin carried as `materials_grounding_pin` on the canonical
  model. The v1.1/v2 `fields`/`non_editorial` extraction is **untouched**.
- **`delta_materials_grounding.py`** (new) — `compute_materials_grounding_benchmark(canonical)`: per-artifact
  `_classify` (accepted_unchanged / grounding_added / grounding_removed / revision_changed / grounding_replaced
  / abstention), fresh-only acceptance headline (preserved excluded), version-skew abstention, non-common
  grounded-artifact transparency, references-only records. `MATERIALS_GROUNDING_VERSION = "v1"`.
- **`delta_auditor.py`** — computes the benchmark and carries it on the report + `materials_grounding_version`
  in provenance.
- **Deferred (not in B):** index/search headline + dashboard surfacing of the metric (mirrors how
  `metadata_accuracy`'s dashboard surfacing was deferred to a joint UI review). The benchmark rides on the
  report body today; no consumer reads a headline yet, so no dead code ships.

## 4. Backward compatibility
Additive: on any revision without materials grounding (all existing/v1.1/v2 data), the benchmark is
NOT-APPLICABLE and nothing else changes. `grounding` is an independent canonical key read only by the new
module; existing consumers (metadata benchmark, geometry, index, report body) read targeted keys and are
unperturbed. Full suite green including all prior metadata/geometry tests.

## 5. Provenance & governance discipline (mirrors metadata v2)
- **Authoritative = per-output `context_source`**, pin used only for versions (the recall carry-forward edge
  is handled: pin present but nothing grounded → not-applicable; per-output classify yields the right result).
- **Fresh-only acceptance** — `preserved_*` outputs excluded from the denominator (equal approved by
  construction); abstention + unsupported_version excluded too.
- **Version-pinned** — `materials_grounding_version` + `resolution_contract_version` on the benchmark; a
  genuine both-sides skew abstains (`unsupported_version`) rather than emit a wrong number.
- **Identifiers/references only** — material_id/category/subtype/edition_id/file_id/revision; **never** material
  bytes or text (asserted by test).

## 6. Adversarial review (two rounds, independent)
**Round 1** found 4; all fixed. **Round 2** verified every fix, no new defect, no regression.

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MAJOR | The pin is emitted per-side only when that side grounds, so grounding introduced at approval (off→on) had one absent pin, misread as a version skew → the whole run abstained, silently defeating `grounding_added`. Masked by a test fixture that always stamped both pins. | Skew only when **both** sides carry a real pin (`None not in gen_pin and None not in app_pin and gen_pin != app_pin`). Fixture now emits pins per-side like production. All four transition shapes (both-ground / on→off / off→on) verified correct. |
| 2 | MINOR | Applicability checked only common artifacts → false `no_materials_grounding` when grounding was only on a non-common (added/removed) artifact. | Applicability spans all outputs; non-common grounded artifacts surfaced as `grounded_only_generated`/`grounded_only_approved`. |
| 3 | MINOR | A `supporting_material` entry with `material_id=None` crashed the whole audit (`sorted([None, str])`). | Id-less entries dropped in `_extract_grounding`; all sorts str-keyed. |
| 4 | NIT | A duplicate `material_id` in one output listed the id twice in the record. | Record id lists deduped (`sorted({...}, key=str)`); consistent with `_classify`'s per-id collapse. |

**Non-blocking (no fix required):** (a) a stale carried-forward pin whose version differs from the other
side's active pin can mark a run `unsupported_version` even though grounding exists — extremely narrow
(needs a contract-version bump between runs + a full grounding-off recall retaining a differing pin),
pre-existing (identical under the old code), and abstaining is the safe branch. (b) A falsy-but-intended
`material_id` (`0`/`""`) would be dropped — out of contract (ids are strings).

## 7. Tests
Full suite **397 pass**. New `tests/test_materials_grounding.py` (16): off-by-default not-applicable; the five
change categories; fresh-only denominator; both-sides version skew; off→on grounding-added (the round-1
regression); non-common grounded applicability; id-less no-crash; duplicate-id dedupe; identifiers-only;
determinism; manual not-applicable; registry-entity filtering; report integration.

## 8. Certification statement
Additive and backward-compatible (NOT-APPLICABLE on all existing data), deterministic, references/identifiers
only (no material text — verified), authoritative off per-output `context_source` with the pin as version-only,
fresh-only acceptance, version-pinned with skew abstention, Publisher-authority + Scout read-only boundary
intact. **Offline-certified.** Remaining gates: merge + deploy (backward-safe), then a coordinated live cert
against a real Publisher revision with `EDENSEEK_MATERIALS_GROUNDING=on` (same drill as the metadata v2/CBI-2b
provenance certs). Build **A** (resolved-graph auditor) follows, per the agreed order.
