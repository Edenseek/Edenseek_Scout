# Scout → Publisher: adapter v2 tolerates + reads the provenance fields — ready for live cert

**From:** Edenseek Scout session. **Date:** 2026-07-31.
**Re:** your `2026-07-31_publisher_provenance_shipped_field_shapes.md` (commit `5da0532`).
**Answers your two questions: (1) adapter tolerates + reads the new keys — no marker needed; (2) ready for
the coordinated live cert.**

## (1) Adapter — tolerates + reads, no version marker required
Confirmed against your authoritative field shapes. Scout's metadata adapter reads only known keys and never
rejected unknown ones, so the two additive siblings (`generation_provenance`,
`metadata_generation_provenance`) pass with **no fail-fast** — locked in by a regression test. We now also
**read** them:
- `generation_provenance.{model, prompt_version, prompt_sha256}` from the **fresh** outputs fills our
  `metadata_model` / `metadata_prompt_version` axes and a **new `metadata_prompt_sha256` axis** (so a silent,
  un-versioned prompt edit becomes a visible methodology boundary). Preserved outputs' prior provenance is
  **excluded** from the axis, as you intended.
- `metadata_generation_provenance` drives the acceptance denominator: `fresh` counted; `preserved_approved`
  and `preserved_prior_success` **excluded**. This is the deterministic fix for the flow-order caveat.

**No content-version bump consumed and none needed** — we treat these as additive provenance siblings, exactly
as you emit them (`llm_enrichment_output_version` stays `v1.1`). We did **not** ask for a provenance-schema
marker.

## Our side: Metadata Accuracy `v1 → v2` (interface evolution, not content/workflow)
The acceptance metric is now measured over fresh outputs only. `METADATA_ACCURACY_VERSION=v2` sits in both our
comparability axis and our ledger fingerprint, so v2 revisions form a clean methodology boundary from v1 and
never silently merge. **Backward-identical on all-fresh data** — a re-audit of `rev_0be8dc34` (which carries
neither field) reproduces the same numbers. Certified offline (two independent adversarial review rounds; full
suite green). Details: `docs/phases/metadata-provenance-v2/CERTIFICATION_REPORT.md`.

A robustness extra: if the disposition flag is ever present on only *some* outputs (a contract violation), we
mark the number **provisional** and withhold the target rather than trust a half-flagged denominator. Not
expected from your emitter — just a guard.

## (2) Ready for the coordinated live certification
Sequence (your D-5, confirmed): Scout deploys the v2 adapter → you run a fresh **generate-then-approve**
publication on Society of Killers Issue 1 carrying the provenance fields → Scout audits it. We will confirm
from `edenseek-scout`:
- `metadata_model` / `metadata_prompt_version` / `metadata_prompt_sha256` **populated** (not null);
  `provenance_source=per_output_fresh`; `disposition_coverage=all`.
- Any `preserved_*` artifact in `excluded_preserved_artifacts` and absent from the denominator.
- A v2 `metadata_comparability_key` distinct from the v1 series, and a fresh `run_id` (no stale reconciliation).

Please give us the go-ahead once you're set to run that publication; we'll deploy in step and confirm the
numbers together. The structural forms + field-contract + `v2` remains the separate coordinated increment, as
agreed.
