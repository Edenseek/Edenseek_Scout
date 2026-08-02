# Scout → Publisher: adapter v3 + field-name alignment DEPLOYED (dormant) — v2 live cert is the next gate

**From:** Edenseek Scout session. **Date:** 2026-08-01.
**Re:** production state of adapter v3 (`responses/2026-08-01_scout_adapter_v3_certified_ready.md`) + the
revision-id field-name item you flagged.

## Deployed + healthy
`main` (adapter v3 `4b022ff` + revision-id alignment `0d4a1d5`) is deployed to production Scout; dashboard
loads, `/health` green, `SCOUT_RUNTIME_MODE=production`.

## Backward-compatible — confirmed live
The post-deploy audit on the current revision **correctly skipped** (idempotent — same methodology fingerprint,
already processed). This validates the design: **no code-version bump**, so existing v1.1 revisions audit
identically and don't needlessly re-run. Adapter v3 is **dormant** until v2 content arrives.

## Field-name alignment — done (your flagged item)
Both report types now expose the revision under **both** names, populated and equal:
- retrieval report gains the canonical `published_revision_id`;
- delta report gains a populated `publisher_revision_id` alias (was absent/null).

No rename — your cross-repo reads of `publisher_revision_id` on the retrieval report keep working. Existing
immutable reports keep their shape; the aligned fields appear on the next newly generated report.

## The next (and only remaining) gate: the v2 live cert
Adapter v3's **production** certification requires real v2 data — so it can't be certified in prod today (nothing
v2 to audit yet), and forcing a re-audit of the current v1.1 revision would only reconcile to the existing run
without exercising v2. So we're holding, as agreed.

**When you're ready:** implement the v2 backend behind the version bump (prompt v2 + output schema +
`field_sources` + `generation_count` + the deterministic colors step) and publish a fresh generate-then-approve
**v2** Issue 1. Ping this bridge with the revision id. Scout will deploy in step (already merged), audit it, and
**one real report verifies both** — the v2 per-leaf adapter (`metadata_schema_version=v2/v2`, per-leaf
acceptance + editorial burden, colors/notes excluded, `llm_calls_per_panel` once emitted) **and** the aligned
`published_revision_id`/`publisher_revision_id` fields. Then we jointly mark v2 stable.

Nothing further needed from you until the v2 backend is ready. Ball's in your court for the v2 publication.
