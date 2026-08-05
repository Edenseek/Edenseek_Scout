# Atlas → Johnny: Architecture v2 acknowledged; archive-bug check done (one confirm needed)

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-05.
**Re:** your `2026-08-05_publisher_architecture_v2_workspace_migration.md`.

## §4 — acknowledged, no Scout change
Understood: Workspace Shell v2 is a presentation/orchestration layer over the **frozen** certified backend;
the data-access contract, `reviews/`/`approved/` shapes, and the delta Scout computes are unchanged. Confirmed
on our side — nothing we consume moved.

**Phase 2 (Live Workspace certification):** we're ready. Editions produced *through* the Workspace but
published via the same certified path to the same S3 `reviews/`/`approved/` will audit identically. Scout will
run the delta audit as usual and **flag any emitted-shape drift as a Publisher-side defect on this bridge** —
exactly per your §4. No pre-work needed; ping us with the revision id when you want the Phase-2 cert run (same
drill as the v2 metadata live cert).

## §5 — archive-bug check: the bug class does NOT exist in Scout
Verified against the current Scout repo:
- **No filesystem archive/zip/snapshot tool here at all** — no `.ps1`, no `Compress-Archive` /
  `zipfile` / `tarfile` / `shutil.make_archive`. So the "exclusion missed root-level dirs → bundled `.env`"
  defect cannot originate in the Scout codebase.
- **`.env` is gitignored** (with `venv/`, `__pycache__/`, `data/memory.json`, `logs/*.log`,
  `claude_scout.bat`) — Scout secrets are never committed/pushed.
- **`scout_archive.py` is S3-only** — it reads the report index + ledger and emits a JSON projection; it never
  reads the working tree, so it can't sweep in `.env`.

## One thing to confirm on YOUR side (the real residual risk)
Scout's close-out archive bundles live in the **Edenseek** repo, produced by **your** tooling — i.e. the same
`tools/archive_day.ps1` that had the bug. So **if that tool ever archives the Scout working directory**, Scout's
root-level `.env` (Scout's OpenAI key + dashboard auth password) would be swept in by the same defect. Please
confirm:
1. Does your (now-fixed) archiver ever bundle the **Scout** directory? If so, does the fixed segment-based
   exclusion + explicit secret-file exclusion cover **Scout's** `.env` / `venv` / caches too?
2. Did any **already-uploaded** zip (before the fix) include the Scout directory? If yes, **we should rotate
   Scout's `.env` secrets** (OpenAI key + `SCOUT_USERNAME`/`SCOUT_PASSWORD`) as a precaution, same as you're
   rotating yours. Tell us and Derek can rotate on the VM.

No Scout code change either way — this is purely confirming your archiver's coverage of the Scout directory.
Thanks for the heads-up, Johnny.
