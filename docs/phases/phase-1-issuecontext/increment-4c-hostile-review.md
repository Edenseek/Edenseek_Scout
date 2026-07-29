# Phase 1 · Increment 4c (thread `context` into the `dataset_auditor` runner) — Hostile Review

**Scope reviewed:** optional `context=None` threaded through `dataset_auditor._resolve_input_dir` and
`run_dataset_audit`; the Scout-repo publication gate widened to `context is not None or is_configured()`.
New test file `tests/test_dataset_auditor_context.py`. No **production** caller passes a context.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **`context=None` is byte-for-byte unchanged.** `git diff main -- dataset_auditor.py` is pure forwarding:
  `_resolve_input_dir` passes `context=context` to `materialize_approved_contract` (Increment 2 already made
  `context=None` identical to the prior no-arg call); `run_dataset_audit` forwards `context` to
  `publish_reports` / `publish_scout_report` (Increment 3 made `context=None` byte-for-byte).
- **The publication gate is unchanged for `context=None`.** `context is not None or is_configured()`
  short-circuits to `is_configured()` when `context is None` — identical to the prior gate.
  `test_context_none_unconfigured_skips_publication` confirms the gate stays closed when unconfigured, and
  `test_context_none_configured_publishes_with_none` confirms it publishes (forwarding `context=None`) when
  configured — exactly today's behavior.
- **Whole-system behavior unchanged.** No production caller passes a context: `app.py`, `scheduler.py`,
  `scout_watch.py` all call `run_dataset_audit()` with no argument (verified by grep), so the certified
  scheduled/manual dataset audit runs the env path untouched. The read-only `analyze_*` endpoints call
  `_resolve_input_dir(input_dir)` with no context → `context=None` → unchanged (they are out of scope for
  this increment and were not modified).

### Context path proven
- `test_forwards_context_to_materialize`: `_resolve_input_dir(None, context=ctx)` calls
  `materialize_approved_contract(context=ctx)`; explicit dir / `SCOUT_DATASET_DIR` still take precedence and
  skip S3 (`test_explicit_dir_wins_and_ignores_context`).
- `test_context_opens_gate_and_is_forwarded`: with the environment **unconfigured** (`is_configured()=False`)
  but a context supplied, publication proceeds and the context is forwarded to **both** publication calls —
  proving the runner both opens the gate on context and threads it through.

### Ownership boundary
- The dataset runner reads the approved contract and writes only via the already-boundary-tested
  `publish_reports` / `publish_scout_report` (writes confined to `edenseek-scout`). This increment adds no
  new write path.

### Scope creep + coupling
- **Only `dataset_auditor.py` changed** (+ the new test file). No Registry/scheduler/dashboard; the
  `analyze_*` read endpoints untouched.
- **No activation.** The runner does not build `context = context or from_env()`; activation remains a later,
  separately-certified step.
- **No new required argument.** Both `_resolve_input_dir` and `run_dataset_audit` default `context=None`.

## Evidence
- `git diff main -- dataset_auditor.py`: pure forwarding + the short-circuit gate.
- New tests: **+6** (`tests/test_dataset_auditor_context.py`), driving the real scoring pipeline over the
  fixture with only side-effect writers + the publication boundary mocked.
- Full suite (venv): **253 passed, 0 failures** (was 247 after 4b).
- `py_compile` clean. No stray filesystem writes from the tests (side-effect writers mocked).

**Increment 4 (4a + 4b + 4c) is now complete: every runner + the evidence read layer accepts and forwards an
optional context, byte-for-byte for `context=None`, with IssueContext still NOT activated in any execution
flow.** Gate to proceed to Increment 5 (thread `context` into the projections — benchmark / archive /
intelligence): founder certification.
