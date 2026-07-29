# Phase 1 · Increment 1 (`scout_context.py`) — Hostile Review

**Scope reviewed:** introduction of `scout_context.py` (`IssueContext`) + `tests/test_scout_context.py`.
**Nothing else changed.** No module imports `IssueContext` yet — this increment adds an unused leaf
abstraction. Reviewed adversarially against `PHASE_1_HOSTILE_REVIEW.md`; assume-guilty until refuted.

## Verdict: PASS (2 intentional observations, both inert in Phase 1)

### Behavioral equivalence (core risk)
- **`from_env()` reproduces today's derivation — proven, not asserted.** `ByteEquivalenceTest` compares
  the context to the modules' *own* private derivations for the same env:
  `approved_prefix == "/".join(audit_s3_source._require_approved_prefix(p))`;
  `(series_id, issue_id) == audit_s3_source._derive_identity_tail(segments)`;
  `(scout_prefix, issue_id) == scout_report_publisher._require_issue_prefix(p)`. If either module's
  normalization changes, the test fails (drift guard). ✅
- **Env contract cannot drift silently.** `EnvContractTest` asserts every env-var name + `DEFAULT_REGION`
  equals the module constants (`a3.BUCKET_ENV`, `srp.PREFIX_ENV`, …). ✅
- **Region default semantics match `os.getenv(name, DEFAULT)`** (absent key → default; present-empty → `""`),
  via `env.get(name, DEFAULT_REGION)`. ✅

### Ownership boundary (must never regress)
- **No I/O.** `scout_context` imports only stdlib + `logging_config`; it builds no S3 client, reads/writes
  nothing. It cannot touch `edenseek-publishing`. ✅
- **Read vs write surfaces cannot be transposed.** Approved (read) must end `approved/`; Scout (write) must
  be `publishers/.../issues/{id}`. Swapping the two env values fails validation fail-loud (covered by
  `test_non_approved_prefix_raises` / `test_scout_prefix_*`). ✅

### Scope creep (Phase 1 must stay Phase 1)
- **Leaf module, no consumers.** No Discovery/Registry/scheduler/dashboard code. `analyzer_registry` and
  `schedule` are inert `None` slots (documented as later-phase). ✅
- **No new required env var.** `from_env` reads only the *existing* vars; no caller is required to build a
  context. Full suite green without any change to callers. ✅

### Failure-mode probes
- Missing/empty env → `IssueContextError` (fail-loud), never a silent wrong-issue. ✅
- Frozen: mutation raises `FrozenInstanceError`; specialization is via `derive()` (immutable copy). ✅

## Two intentional observations (record for the threading increments; inert now)

1. **Cross-prefix identity check is NEW.** `from_env` fails loud if the approved and Scout prefixes disagree
   on `series_id`/`issue_id` (`test_identity_mismatch_between_prefixes_raises`). Today's modules never
   compare the two prefixes, so a mis-set pair (approved→issue_001, scout→issue_002) would today silently
   read one issue and write another. This is a **strengthening**, inert in Phase 1 (nothing calls `from_env`).
   When `context` is threaded into the read/write paths, confirm production's two prefixes are consistent
   (they are — same issue) so this raises for no real config.
2. **`from_env` always requires the full `series/issues` identity on the approved prefix.** The
   *dataset-audit* path requires this today (`materialize_approved_contract` → `_derive_identity_tail`); the
   *delta-only* path (`resolve_current_revision`) does not. Since production uses one
   `SCOUT_APPROVED_S3_PREFIX` for both, the identity is already mandatory in practice. The canonical context
   deliberately requires the full identity that the fuller path needs. No production config is affected.

## Evidence
- `python -m unittest tests.test_scout_context` → **23 passed**.
- Full suite (venv): `python -m unittest discover -s tests` → **226 passed, 0 failures**.
- `python -m py_compile scout_context.py tests/test_scout_context.py` → clean.

**Gate to proceed to Increment 2 (thread `context` into the read path):** founder certification of this
increment. Until then, no further modules are touched.
