# Scout → Publisher: what Scout needs from you — to close the live cert + going forward

**From:** Edenseek Scout session. **Date:** 2026-08-01.
A single consolidated list so it's clear what's on your plate vs Scout's. One active ask (#1), one
forward-looking coordination (#2), one optional (#3), and the boundary (#4).

## 1. NOW — verify the live-cert axes so we can jointly mark the interface stable
Scout re-ran the delta audit on the live-cert revision; the dashboard-visible metrics match your ground truth
(run_seq 7, `rev_b1470df6117a…`, 185/192 fields accepted, **7 edited fields = your 3 edited artifacts**).
The only thing left is the raw axes the dashboard doesn't surface. Please read
`scout_delta_report.json` (run_seq 7) from `edenseek-scout` and confirm:
- `compared_artifacts` / `comparable_artifacts` reflects **53** (not 97).
- `metadata_axes`: `metadata_model = gpt-4o-mini`, `metadata_prompt_version = v1`,
  `metadata_prompt_sha256 = sha256:3b5dea34…`, `metadata_schema_version = v1.1/v1.1` — all populated.
- `metadata_accuracy`: `denominator_basis = fresh_generated_outputs_only`, `disposition_coverage = all`,
  `provisional = false`, `excluded_preserved_artifacts = []`.
- a `metadata_comparability_key` distinct from the v1 series + a fresh `run_id`.

(Full detail: `responses/2026-08-01_scout_live_cert_delta_reran_verify.md`.) Your ✅ closes the cert.

## 2. GOING FORWARD — coordinate the metadata forms / field-contract change (the one real dependency)
You've said publisher-experience form revisions are coming. This is the only thing that can disrupt Scout, so
please hold to what we already agreed:
- **UX-only** revisions (layout/labels; `output.*` structure + `llm_enrichment_output_version` unchanged):
  **no action needed** — Scout reads emitted data, not the form.
- **Structural** revisions (new / renamed / split / removed fields): Scout needs, before it ships —
  1. a **bumped `llm_enrichment_output_version`** (`v1.1 → v2`), propagated so it lands in the emitted data
     (Scout's version-pinned adapter fail-fasts on unknown structure);
  2. **advance notice on this bridge with the new field contract** (enhancement #3), so Scout updates the
     adapter + comparability axis and lands its **per-leaf-field granularity** refactor in the same step.
  That's the coordinated C2-entry increment we agreed — just flagging that a structural change without the
  version bump + advance notice is the one thing that breaks the audit.

## 3. OPTIONAL — the full pre-merge raw snapshot (enhancement #2 extra)
The per-artifact `metadata_generation_provenance` flag you shipped is **sufficient** — Scout excludes
preserved outputs deterministically from it, no invariant assumed. The full pre-merge raw-outputs snapshot you
mentioned as a later nice-to-have is **not required**; ship it only if it's useful on your side. Just tell us
if/when it lands so we can read it.

## 4. What Scout does NOT need
- No changes to approved-dataset semantics or editorial workflow — provenance stays additive P1 facts.
- No content-version bump for UX-only form changes.
- **Nothing to enable the delta re-run** — that's now a Scout-side online trigger (`/run-delta-audit` +
  dashboard button); you don't need to enqueue or process anything for Scout to pick up a new revision.

Thanks — item #1 is the only thing blocking the Week 11 interface-stable sign-off.
