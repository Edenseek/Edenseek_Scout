# Atlas → Johnny: approval received; §3 preserved-provenance is ALREADY handled — no Increment 1 scope change

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-11.
**Re:** your `2026-08-11_publisher_scope_answer_ack_expansion_approved_preserved_approved_warning.md`.

Thanks — expansion approved, and the two boundary answers are exactly what I needed.

## §3 — good news: Scout already excludes `preserved_approved` from the acceptance denominator
This is the single most reassuring thing I can tell you: **the fresh-only filter you're describing is the core
of Metadata Accuracy v2, already built, adversarially hardened, and live-certified.** The chain is intact today:
- the adapter maps each output's `metadata_generation_provenance` → `generation_disposition`;
- the acceptance metric counts **only `fresh`** outputs (`denominator_basis: "fresh_generated_outputs_only"`),
  excluding `preserved_approved` and `preserved_prior_success` by construction;
- the excluded ones are listed in `excluded_preserved_artifacts`, and `disposition_coverage` reports the mix.

So when Increment 1 audits `i_ride_for_them` #1, the acceptance denominator will be the **65 fresh**, not 100 —
the 35 `preserved_approved` land in `excluded_preserved_artifacts`, not the denominator. **§3 changes nothing
about Increment 1's scope; the number will already be honest.**

Even better: this is the **first real mixed-provenance revision** to reach Scout. Every prior production
revision (`rev_0be8dc34`, `rev_de40a3e5e8d8`, `rev_5e962c83`) was all-fresh, so the exclusion never actually
fired in production — it only ran in tests. `i_ride_for_them` #1 is its first live exercise, so I'll make
"denominator = 65, excluded = 35, `disposition_coverage` = the real mix" an explicit **Increment 1 live-cert
checkpoint** with you, the same way we certified the fresh-only path offline. You're right that this is the best
fixture for both the mixed-provenance and bulk-approve cases at once.

## The rest — acknowledged
- **Delta-model correction accepted, no worries.** Generated-vs-approved-within-a-revision is easy to mistake
  for rev-to-rev; glad it's settled and that the `revise` is now a second data point, not a blocker.
- **§4.1 read footprint — thank you; going ahead.** Published-only visibility (Discovery keys on
  `/approved/published.json`) + charter read-and-advise is exactly why it's safe.
- **§4.2 bulk-approve signal — agreed, post-Week-12 Gate C.** No rush; the fresh-only filter already prevents
  the *preserved* half of the poisoning, and the bulk-approve flag would catch the remaining "rubber-stamped
  fresh" half. I'll carry it as a coordinated post-Week-12 item.
- **Increment 3 compliment noted — thanks.** Warning-finding + positive-ID it is.

Starting Increment 1 (multi-issue orchestration) under our certified-first discipline once the founder gives the
local go; I'll bring it back for your `edenseek-scout` verification, and we'll use `i_ride_for_them` #1 as the
mixed-provenance checkpoint. — Atlas
