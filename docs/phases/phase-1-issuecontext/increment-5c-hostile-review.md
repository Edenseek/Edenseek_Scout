# Phase 1 · Increment 5c (thread `context` into `scout_intelligence`) — Hostile Review

**Scope reviewed:** optional `context=None` on `scout_intelligence.build_geometry_intelligence` and
`build_metadata_intelligence`, forwarded to the already-threaded `sri.load_index` (both) and
`srp.read_object` (metadata per-field detail). The pure projections `geometry_intelligence` /
`metadata_intelligence` are unchanged.

## Verdict: PASS

### Behavioral equivalence
- **`context=None` is byte-for-byte unchanged.** `git diff main -- scout_intelligence.py` is four lines:
  the two signatures gain `context=None`, and the `load_index` / `read_object` calls gain `context=context`.
  With `context=None`, both delegates are the prior calls (certified byte-for-byte in Increment 3a/3b). No
  other logic changed.
- **Context path == env path.** `test_geometry_intelligence_context_equals_env` and
  `test_metadata_intelligence_context_equals_env` build the intelligence over a seeded index under the env
  default vs an explicit context **with the environment cleared**, asserting identical results.
- **read_object forwarding proven.** `test_metadata_forwards_context_to_load_index_and_read_object` uses a
  metadata-comparable entry and asserts the context reaches **both** `sri.load_index` and `srp.read_object`
  (the read of the per-field history report).
- **Whole-system behavior unchanged.** Production callers `app.py:332` (`build_geometry_intelligence()`) and
  `app.py:343` (`build_metadata_intelligence()`) pass no context → the certified env path.

### Scope + boundary
- **Read-only loaders.** No writes; no new write path.
- **Only `scout_intelligence.py` changed** (+ its test). No activation (`from_env()` not introduced); no new
  required argument.

## Evidence
- `git diff main -- scout_intelligence.py`: two signatures + two delegate calls only.
- New tests: **+3** (`TestIntelligenceIssueContextThreading`).
- Full suite (venv): **260 passed, 0 failures** (was 257 after 5b).
- `py_compile` clean.

## Increment 5 complete (5a + 5b + 5c)
All three projections — `scout_benchmark`, `scout_archive`, `scout_intelligence` — now accept and forward an
optional context, byte-for-byte for `context=None`, with **`IssueContext` still not activated** in any
execution flow. With Increments 1–5 done, every read, write, index, ledger, runner, and projection accepts
an optional context; `from_env()` is used **only** by `IssueContext.from_env` itself and nowhere in the
execution path. **The remaining Phase-1 step is the runbook §"Confirm `app.py`/`scheduler.py`/
`scout_watch.py`/`static/index.html` unchanged" check, followed by the single-issue production re-cert** —
activation of `from_env()` in the flow remains a later, explicitly-certified decision.
