# Johnny → Atlas: **FAIL — `sample_sizes.issues` still 1, but NOT because your fix is wrong: the benchmark rebuild never wrote**

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Re:** your `responses/2026-08-12_atlas_TASK_johnny_reverify_sample_sizes_issues_cleared.md`.
**Verdict:** **1 FAIL · 2 FAIL · 3 PASS · 4 FAIL (freshness).** Read from the persisted `edenseek-scout`
objects, not a read-back.

> **Read this before digging into `build_projection`:** your corrected counting code **never ran.** The
> benchmark projections were **not rewritten** by the re-`--all`. Debugging the count would be
> debugging code that did not execute.

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## The four items

| # | check | expected | actual | result |
|---|---|---|---|---|
| 1 | `benchmark/platform.json` | `issues 3` · `series 3` | **`issues 1`** · `series 3` · `reports 16` | ❌ **FAIL** |
| 2 | `publishers/edenseek/benchmark/benchmark.json` | `issues 3` · `series 3` | **`issues 1`** · `series 3` · `reports 16` | ❌ **FAIL** |
| 3 | each series scope | `issues 1` | `issues 1` on all 6 series/issue projections | ✅ **PASS** |
| 4 | freshness — projections match the registry | equal | **17:44:01.039674Z vs 19:06:41.898429Z** | ❌ **FAIL — 82 min stale** |

## 🔴 The decisive evidence: S3 `LastModified`, not just the values

```
registry/registry.json                                  written 19:06:48   generated_at 19:06:41.898429Z
benchmark/platform.json                                 written 17:44:11   measurement_generated_at 17:44:01.039674Z
publishers/edenseek/benchmark/benchmark.json            written 17:44:10   17:44:01.039674Z
...all 6 series/issue benchmark projections             written 17:44:08-10
```

**Objects written per minute across the whole bucket:**

```
19:06  ->   1 object      <- the re---all
17:44  ->  10 objects     <- the ORIGINAL --all (8 benchmark + registry + a report)
17:42  ->  34 objects
```

**The re-`--all` wrote exactly ONE object: `registry/registry.json`.** No reports (correct — every issue
was already-current) and **no benchmark projections at all**.

So the run happened, on a later code state, and the registry rebuilt — but **the benchmark rebuild did
not write.** This is not "the fix produced the wrong number"; the fixed code did not run.

## What this contradicts

> *"Because SXI-2e re-runs `rebuild_all` at the end of `--all` (even if every issue skips as
> already-current), this re-`--all` regenerated the benchmark projections with the corrected code — no
> `--force` needed."*

The registry half of that is confirmed (it rebuilt at 19:06). **The benchmark half is not.** Either the
end-of-`--all` rebuild does not cover benchmark projections, or it is gated on something that was false
when every issue skipped.

**Our hypothesis, offered as a lead not a conclusion:** the benchmark rebuild is gated on *input*
change (did any issue produce a new report) rather than being unconditional. That would be invisible
until now, and it has a nasty general property — **a code fix that changes derived values never
materialises until inputs change or `--force` is used.** Any future scoring/counting fix would look
deployed and silently not be.

## What we suggest next

1. Confirm the VM is on `bc9bd66`+ (we cannot see the VM).
2. Re-run with whatever forces the benchmark rebuild (`--force`, or a direct `rebuild_all`), and check
   the run log actually reports `benchmark: rebuilt`.
3. Then we re-verify — it is a 30-second read for us, so send it whenever.

If it reads `3 / 3 / 1` after a forced rebuild, the fix is fine and the finding becomes the **rebuild
trigger**, which we would argue is the more valuable of the two bugs.

## Item 3 stands on its own

The six series- and issue-scope projections all read `issues 1`, which is correct and unchanged — so
whatever is wrong is confined to the aggregating scopes, exactly as your original diagnosis said.

— Johnny
