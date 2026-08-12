# Certification Report — SXI-2c (per-scope benchmarks + cross-issue Intelligence + comparability guard)

**Track:** Scout Expansion Increment 2 · sub-increment **2c** (the analytical-depth server layer)
**Branch:** `week12-sxi2c-scoped-benchmarks-intelligence`
**Date:** 2026-08-12 · **Discipline:** certified-first (build → adversarial review → certify → deploy → verify)
**Status:** CODE-COMPLETE · adversarially reviewed · offline-certified · HELD for merge → deploy

---

## 1. What changed and why

The observability/health layer was already publisher-wide, but the **metric** layer (benchmarks +
intelligence) was single-issue: `/benchmark/{level}` served only `platform`, and the intelligence loaders
were hardwired to the env-configured issue. SXI-2c completes the **server-side** multi-issue analytical
layer so a consumer can ask "recurring failure modes for this whole series / publisher", not just one
issue. The front-end comparison views (series-vs-series) are **2d** — 2c is the certified data layer they
consume. Read-only; no contract change.

## 2. Changes

**`app.py`**
- `_benchmark_key(level, issue_prefix)` (new) — derives the persisted benchmark key from level + scope via
  `scout_benchmark._roots(issue_prefix)`, the SAME ownership-chain parse `rebuild_all` used to WRITE the
  objects, so a read serves exactly what was persisted. Bad level / missing scope / malformed prefix → 400.
- `/benchmark/{level}` now serves `platform | publisher | series | issue` (non-platform take an
  `issue_prefix`, whose series/publisher root is derived).
- `/intelligence/geometry` and `/intelligence/metadata` gained optional `level` + `issue_prefix`: when
  `level` is set, the cross-issue scoped loader runs; empty `level` keeps the single-issue behavior
  (byte-identical), optionally scoped to an `issue_prefix` via `_issue_context`. `ValueError`/`KeyError`/
  `IndexError` from scope resolution → 400 (re-raised before the broad 503 handler).

**`scout_intelligence.py`**
- `_scope_and_prefix(level, issue_prefix)` — returns `(scope dict, issue-prefix filter)`, mirroring
  `rebuild_all`'s per-level scope construction EXACTLY, so Intelligence and Benchmarks agree on what a scope
  means.
- `_scoped_entries(client, bucket, prefix, needs_reports)` — enumerates every per-issue index via
  `sb.discover_issue_indexes`, filters to `issue_prefix == prefix or startswith(prefix + "/")`, merges
  entries, and (for metadata) loads the immutable reports by absolute key from the shared scout bucket.
- `build_geometry_intelligence_scoped` / `build_metadata_intelligence_scoped` — enumerate → filter → project
  at a scope.

## 3. The comparability guard (the correctness heart)

Aggregating metrics across issues must never average across methodologies. This is **inherited, not
re-implemented**: `geometry_intelligence` / `metadata_intelligence` group the merged entries by
comparability key (`geometry_comparability_key` / metadata axes) via `sb.build_projection`, which keys its
segments by comparability key. So entries produced under different methodologies land in **separate
segments** and are never combined — whether they come from one issue or many. Proven by
`test_different_keys_never_averaged_across_issues`: two geometry keys spread across three issues →
`sample_sizes.segments == 2` (not 1), segment keys `{cmp_gA, cmp_gB}`.

## 4. Boundary / safety

Read-only. The one user-supplied input (`issue_prefix`) is validated by `_roots` (requires the
publishers/title_groups/series/issues chain → 400 otherwise); a crafted prefix builds an S3 key in a flat
keyspace, so at worst it reads a nonexistent key → 404/None, no escape. Prefix filtering uses
`== prefix or startswith(prefix + "/")` so a sibling sharing a string prefix (`soc` vs `soc2`) is not
wrongly included (regression-tested). Cross-issue reads use the shared scout bucket + absolute keys; an
unreadable report drops from per-field detail without failing the projection.

## 5. Tests

Full suite **481 passed** (+14). New `tests/test_sxi2c_scoping.py`: `_scope_and_prefix` per level + bad
level/prefix; `_scoped_entries` filtering (platform/series/issue/publisher) + prefix boundary-safety; the
comparability guard (different keys → separate segments across issues; series scope excludes other series);
benchmark endpoint (auth, bad level → 400, non-platform without scope → 400, malformed scope → 400, platform
+ series key resolution); intelligence scope param (bad scope → 400, scoped path calls the scoped loader).

## 6. Adversarial review (one round + fold)

**Verdict: safe to merge + deploy.** The reviewer verified the core claims empirically: the comparability
guard genuinely holds (segmentation is keyed strictly by the per-entry comparability key in
`build_projection`, independent of issue — a cross-issue merge cannot collide two methodologies); the prefix
filter's `+ "/"` boundary correctly excludes a leading-string sibling (`society_of_killers` vs
`…_killers2`); and `_benchmark_key` cannot be injected (a crafted prefix only ever builds another
canonical key → 404, S3 flat keyspace). Error handling and single-issue backward-compat are correct.

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MINOR | The boundary test seeded `i_ride_for_them` as the "other" series — which diverges at `title_groups`, so it was excluded even by the *buggy* `startswith(prefix)` form. The test passed with or without the guard → not a real regression barrier. | **Fixed** — added a genuine leading-string sibling (`society_of_killers2`, `I4`) to the seed; the series scope now asserts `len == 3` (excludes I4), which fails on the un-`/`-terminated form. |
| 2 | MINOR (latent) | If a caller ever passed a `context` whose `scout_bucket` differed from the env var, `_scoped_entries` enumerated via `context.scout_bucket` but read reports via `read_object(client, key)` (env) — a split-bucket read. Unreachable on the HTTP path (context is a dead param there), but inconsistent with the single-issue loader. | **Fixed** — `_scoped_entries` now takes `context` and forwards it to `read_object`, matching the single-issue loader; enumeration and reads can never split. |
| 3 | (gap) | No test asserted the `level==""` backward-compat fallback. | **Added** `test_default_path_still_single_issue` (no level → single-issue loader, `context=None`, scoped loader not called). |

Documented NITs (accepted, not fixed):
- **Mislabelled diagnostics:** a genuine `KeyError`/`IndexError` from deep inside a projection over a
  malformed entry would surface as 400 "Invalid scope" rather than 503. Theoretical — the reviewer could
  not construct one given the upstream `.get()`/filter guards.
- **Uncached whole-bucket scan:** every `/intelligence/*` scoped call lists the entire `publishers/`
  keyspace and GETs every index per request (no cache/pagination cap). Fine at current scale (a few issues);
  a caching/pagination follow-up when the bucket grows. Not a correctness issue.

## 7. Certification statement

Additive, read-only, server-side completion of the per-scope metric layer; the comparability guard is
inherited from the certified per-key segmentation and explicitly re-proven across issues (now with a real
boundary sibling); the one user-supplied prefix is validated; single-issue behavior is unchanged and tested.
Adversarial review found no correctness defect; two MINORs (a non-catching test, a latent context/bucket
inconsistency) are fixed, one test gap closed. Suite **482 passed**. **Offline-certified.** Remaining gates:
merge → deploy (`git pull` + restart) → (2d) build the front-end comparison views that consume these
endpoints.
