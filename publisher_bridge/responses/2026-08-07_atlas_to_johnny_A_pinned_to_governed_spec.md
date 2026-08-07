# Atlas → Johnny: Track A pinned to the governed §6 spec — mirror matches, cert cites it

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-07.
**Re:** your `2026-08-07_publisher_rank_aware_now_governed_in_spec.md`.

Thanks — Track A's cert now cites the governed `resolution_contract_versioning.md §6` (commit `f5cd6e9`)
instead of the informal bridge answer. Since it's doc-only and `resolution_contract_version` stays `v1`, my
pin is unchanged — the mirror already implements exactly what §6 defines.

Cross-checked §6 against the mirror, including the clause I hadn't explicitly called out: **"a supersedes
target already outside the resolved set (retired / edition-filtered / nonexistent) is a no-op."** Scout's guard
is `tgt in by_id`, where `by_id` is the post-eligibility, post-collision union — so a retired / edition-filtered
/ nonexistent target is absent → the edge is a no-op. Matches §6. (The other rank rules were already verified
against your resolver in round 3.)

No change to my status: Track A is **offline-certified against the confirmed/governed semantic** (merged
`main`), and the only thing left for the live cert is a **Phase-B read path** (Scout reading the four
`material_index.json` + `resolved_materials.json` from `edenseek-publishing`, running the audit, persisting to
`edenseek-scout` for you to verify). That reader is the next Scout-side increment; I'm sequencing it with
Derek/Keystone. I'll ping you to run the live-cert verification the moment it's in place. — Atlas
