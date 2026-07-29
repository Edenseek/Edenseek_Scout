# Phase 1 · Increment 5a (thread `context` into `scout_benchmark`) — Hostile Review

**Scope reviewed:** optional `context=None` on `scout_benchmark.rebuild_all` and `load_projection`.
`scout_benchmark` is a **bucket-wide** projection (it discovers every per-issue index under `publishers/`
and writes issue/series/publisher/platform rollups), so it reads only `BUCKET_ENV` + `REGION_ENV` — the
context sources `scout_bucket` + `scout_region` (its per-issue prefix is irrelevant here). No production
caller passes a context.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **`context=None` is byte-for-byte unchanged.** `git diff main -- scout_benchmark.py`: the env branch is
  the same statements re-indented under a new `else:`; the error message is identical; the region read moves
  into a `region` variable used by the shared `client = client or srp._s3_client(region)` — for the env path
  `region == os.getenv(REGION_ENV, DEFAULT_REGION)`, so the client is built from the identical value (same as
  the prior inline `_s3_client(os.getenv(...))`).
- **Context path == env path — byte level.** `test_rebuild_all_context_equals_env` seeds two issues, runs
  `rebuild_all` under the env default vs an explicit context **with the environment cleared**, and asserts
  the returned key map is equal **and the entire in-memory S3 store is byte-identical** (the discovery +
  weighted projections are deterministic at a fixed `generated_at`). `test_load_projection_context_equals_env`
  asserts identical loaded projections.
- **Whole-system behavior unchanged.** No production caller passes a context: `app.py`
  (`load_projection(keys[level])`) calls with none, and `rebuild_all` has no caller in
  `app.py`/`scheduler.py`/`scout_watch.py`. So `context=None` → the certified env path.

### Ownership boundary
- **Context run writes only `edenseek-scout`.** `test_context_writes_only_scout_bucket` asserts every write
  lands in the scout bucket. Benchmark adds no new write path (still `_persist` → `srp._put`/`_verify_readback`).

### Scope creep + coupling
- **Only `scout_benchmark.py` changed** (+ its test). No Registry/scheduler/dashboard.
- **No activation.** No `from_env()`; the context is purely forwarded/optional.
- **No new required argument.** Both entry points default `context=None`.

## Evidence
- `git diff main -- scout_benchmark.py`: env path = balanced re-indent + region-variable extraction (same value).
- New tests: **+3** (`TestBenchmarkIssueContextThreading`).
- Full suite (venv): **256 passed, 0 failures** (was 253 after 4c).
- `py_compile` clean.

**Gate to proceed to Increment 5b (`scout_archive` — a trivial delegation to the already-threaded
`load_index`/`load_ledger`):** founder certification.
