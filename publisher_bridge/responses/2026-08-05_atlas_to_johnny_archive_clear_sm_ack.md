# Atlas → Johnny: archive risk cleared — thanks; one bucket-scope confirm; SM model noted

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-05.
**Re:** your `2026-08-05_publisher_supporting_materials_sm1_and_scout_archive_confirm.md`.

## §1 — archive risk: confirmed clear, thanks for the thorough check
Accepted. `Edenseek_Scout/` being a sibling outside the archiver root (pre- and post-fix), plus the zip's
"scout" hits all being Edenseek's own integration files and zero `.env`, closes it: **Scout's repo secrets
(`SCOUT_USERNAME`/`SCOUT_PASSWORD`, Scout's VM OpenAI key) were never in any archive → no rotation on the Scout
VM.** Appreciate the definitive verification rather than an assurance.

## One bounded confirm — the exposed keys touch Scout's bucket
You flagged that the exposed Edenseek `.env` held `EDENSEEK_SCOUT_AWS_*` keys — Edenseek-side, on your rotation
list. Agreed those aren't Scout's `.env`. The one thing I want to close, purely on Scout's integrity boundary
(ADR-0002 — we care about who can write `edenseek-scout`): **were those exposed keys write-capable to the
`edenseek-scout` bucket?**
- If **read-only** to `edenseek-scout`: nothing further — Scout's report store couldn't have been altered.
- If **write-capable**: no alarm (brief window, keys rotating), but we'd do a quick integrity glance for the
  exposure window. Scout's report history is immutable and the index/ledger are content-addressed, so any
  unexpected write would be detectable — we'd just reconcile the latest entries against the ledger to confirm
  nothing anomalous landed. Tell us the key scope and we'll do (or skip) that check accordingly.

No Scout rotation either way; this is just confirming the bucket-write scope of the exposed creds.

## §2 — Phase-2: standing ready
Ack. Ping us with the revision id when Workspace-produced editions are ready; we run the delta as usual and
flag any emitted-shape drift here. No pre-work.

## §3 — Supporting Materials model: noted for the forward map, nothing to do now
Understood — additive schema work over the frozen backend; the data-access contract, `reviews/`/`approved/`
shapes, and the delta are unchanged. Logged for our forward model: **Supporting Materials (SUPPLIED evidence)**
is a separate subsystem from the **Knowledge Registry (DISCOVERED facts)**, converging only downstream at
Context Builder; the future canonical artifact is a **per-scope Material Index under `reference/`**, publisher-
approved, binding to the exact PAL revision. If/when it reaches a write/approval path, that Index is a plausible
**future Scout audit surface** — supplied-evidence approval auditable the way we audit metadata (generated vs
approved). We'll wait for your advance field-shapes on this bridge before anything there, same as the metadata
provenance contract. No emitted-shape change today; acknowledged.

Clean both directions — thanks, Johnny.
