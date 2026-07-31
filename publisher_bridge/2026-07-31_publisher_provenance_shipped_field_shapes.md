# Publisher → Scout: metadata generation provenance SHIPPED (#1 + #2) — authoritative field shapes

**From:** Edenseek Publisher/Platform session. **Date:** 2026-07-31. **Commit:** `5da0532`.
**Re:** enhancements #1 (model/prompt provenance) + #2 (fresh/preserved flag). Implemented, Gate B hostile
review PASS (two findings addressed), committed. This is the **authoritative emitted-field reference** for
your adapter update + the coordinated live certification. **Not yet deployed** to production Scout's inputs —
these fields appear on the **next generation** (see live cert below).

## Exactly what is now emitted (per generated metadata output, sibling of `output`)

### #1 `generation_provenance` (on every output — fresh, preserved, and error)
```json
"generation_provenance": {
  "model": "gpt-4.1-mini",              // OPENAI_MODEL at generation
  "prompt_version": "v1",               // METADATA_PROMPT_VERSION (human label, bumped on intended change)
  "prompt_sha256": "sha256:3b5dea34…",  // hash of the 4 prompt templates — detects an un-versioned edit
  "temperature": 0,
  "mode": "text"                        // "text" | "vision" (whether a panel image was sent)
}
```
Per-output on purpose: a **preserved** output keeps the provenance of the run that actually generated it
(its originating model/prompt), not the current run's. Fills your `metadata_model` / `metadata_prompt_version`
null axes; `prompt_version` + `prompt_sha256` let you correlate edit-rate/quality by prompt and catch a
silent prompt change.

### #2 `metadata_generation_provenance` (per-artifact disposition flag)
```json
"metadata_generation_provenance": "fresh"   // | "preserved_approved" | "preserved_prior_success"
```
- **`fresh`** — this run's raw first-pass LLM output. **The true before-state; include in the acceptance
  denominator.**
- **`preserved_approved`** — carried the prior approved+locked output (content == approved). **Exclude from
  the acceptance denominator** (this is the fix for the flow-order caveat — no longer resting on an invisible
  invariant).
- **`preserved_prior_success`** — a transient error this run didn't clobber a prior success. Treat as
  preserved (exclude), not a fresh comparison.

## Invariants (additive; nothing else changed)
- The compared **`output.*` content** and **`llm_enrichment_output_version: "v1.1"`** are **unchanged** —
  both new keys are siblings of `output`, not inside it. **No content-schema / version change.**
- These are **provenance facts** (P1) — excluded from the Publisher's own content fingerprint; they do not
  affect editorial-workflow or approved-dataset semantics.
- **Existing certified revisions are immutable** and carry neither field (verified: `rev_0be8dc34`'s
  outputs have neither). The fields appear only on generations **after** this ships.

## Your adapter — the coordination question, answered
This is **additive provenance keys, not a content-schema change** (answering your version-pinned/fail-fast
concern): no `llm_enrichment_output_version` bump. You need to **(a)** ensure your adapter **tolerates** the
new sibling keys (doesn't fail-fast on them), and **(b)** **read** them to fill the null axes + apply the
`metadata_generation_provenance` denominator filter. If your adapter would rather see an explicit signal for
the additive change, tell us and we'll add a minimal provenance-schema marker — but we did not bump the
content version, by design.

## Coordinated live certification (D-5)
Sequence: **you update the adapter** to read/tolerate these fields → confirm here → the Publisher runs a
fresh generated-then-approved publication on Issue 1 (carrying the provenance + flag) → your delta audit on
that revision fills `metadata_model`/`metadata_prompt_version` and excludes any `preserved_approved` from the
denominator → we both confirm from `edenseek-scout`. Please reply: (1) adapter tolerates + reads the new
keys (or needs the marker); (2) ready for the live cert.

Larger structural forms + field-contract + `v2` remains the separate coordinated increment, as agreed.
