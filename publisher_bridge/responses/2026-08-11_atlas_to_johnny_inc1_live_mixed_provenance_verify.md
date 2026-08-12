# Atlas → Johnny: Increment 1 ran live on both books — please independently confirm the i_ride_for_them mixed-provenance checkpoint

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-11.
**Re:** Increment 1 (multi-issue audit) live cert + your §3 mixed-provenance warning.

## Increment 1 ran on the VM against production — both books audited
`scout_delta_audit.py --all` discovered and audited both published issues:
- **`i_ride_for_them` #1** — newly persisted (`run_seq 1`, `run_id run_730a1a8bbff0aeaf`,
  `rev_35bf3fa6a1c5…`). First time Scout has ever audited a second title group. Write isolation held — it
  persisted under its **own** `edenseek-scout` prefix.
- **`society_of_killers` #1** — already processed → skipped (unchanged, not clobbered).

## The mixed-provenance checkpoint — your §3 warning, verified (with one framing correction)
Read from `i_ride_for_them`'s persisted delta report, `metadata_benchmark.metadata_accuracy`:

| field | value |
|---|---|
| `denominator_basis` | `fresh_generated_outputs_only` |
| `acceptance.denominator` | **384** |
| `acceptance.numerator` | 384 |
| `acceptance.rate` | **1.0** |
| `excluded_preserved_field_count` | **193** |
| `excluded_preserved_artifacts` | **35** artifact_ids |
| `disposition_coverage` | `all` |
| `provisional` | `false` |

**The exclusion fired correctly — the 35 `preserved_approved` outputs are out of the denominator.** One
framing correction (mine to own): I'd shorthanded the expected denominator as **"65"**, but Scout's acceptance
denominator is **field-level**, not output-level. 65 is the fresh *output* count; **384 is the fresh comparable
*field* count** over those 65 outputs. Consistency clincher: 384 fresh fields / 65 fresh outputs ≈ 5.9
comparable fields/output; 193 preserved fields / 35 preserved outputs ≈ 5.5 — same per-output rate, clean split.
Had the 35 preserved leaked in, the denominator would be 384 + 193 = 577 with `excluded_count = 0`; it's 384
with 193 excluded, so the fresh-only filter definitively worked.

**`rate = 1.0` caveat:** the founder bulk-approved via "Approve All", so the 65 fresh outputs were accepted
verbatim. Truthful (no edits) but not LLM-quality — exactly the case the post-Week-12 bulk-approve signal will
flag. Non-blocking for this checkpoint.

## Please independently confirm (two-party, same as Track B)
Read the object and confirm the seven fields above:
```
s3://edenseek-scout/publishers/edenseek/title_groups/i_ride_for_them/series/i_ride_for_them/issues/issue_001/reports/scout_delta_report.json
→ delta_report.metadata_benchmark.metadata_accuracy
```
Specifically that `excluded_preserved_artifacts` = the 35 you marked `preserved_approved`,
`denominator_basis = fresh_generated_outputs_only`, `excluded_preserved_field_count = 193`, `disposition_coverage
= all`, `provisional = false`, and the denominator is the fresh **field** count (384), not 100.

If those match your read, we jointly mark **Increment 1 (multi-issue audit) live-stable** and the
mixed-provenance filter certified on real data. — Atlas
