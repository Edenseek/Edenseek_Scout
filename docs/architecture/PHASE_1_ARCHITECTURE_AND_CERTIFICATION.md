# Phase 1 — Architecture & Certification Report

> **Canonical architectural reference for the certified Phase 1 baseline.**
> Companion to `ADR-0001-scout-publisher-observability-architecture.md` (frozen) and
> `PRINCIPLES.md` (Principle P1). Where an implementation detail conflicts with `SCOUT_CHARTER.md`
> or ADR-0001, those govern.
>
> - **Baseline commit:** `main` @ `fe07303` (merge of PR #2, `phase-1-issuecontext`).
> - **Rollback point:** pre-merge `main` @ `b24d058`.
> - **Certified:** 2026-07-29. Full suite **260 passed**; single-issue production re-cert idempotent.
> - **Scope:** behavior-neutral. **Not deployed to the Oracle VM** (a separate later decision).

---

## 1. Executive summary

Phase 1 introduced **`IssueContext`** — the canonical, immutable per-issue execution context — and threaded
it as an **optional** parameter (`context=None`) through every layer of Scout's audit pipeline: the
Approved-Dataset read adapter, the evidence layer, the two runners, persistence, the index, the ledger, and
all three projections.

The refactor is **behavior-neutral by construction**: when `context is None` (which every production caller
passes today) each layer executes the pre-existing environment-driven code path **byte-for-byte**. When an
explicit `IssueContext` is supplied, it drives the same code with no environment dependency. This was proven
per layer with env-vs-context equivalence tests (identical S3 keys + byte-identical stored objects with the
environment cleared) and end-to-end by a **single-issue production re-certification** that reproduced the
certified `run000003` logical run exactly (`run_id run_833dfc915be60481`, fingerprint `fp_580cbeb1f41b`) and
reconciled idempotently.

`IssueContext` is **not yet activated**: `from_env()` is never called in the execution path. Phase 1
delivers the *substrate* on which Phase 2 (Discovery → Registry) and later multi-issue / scheduled /
analyzer-registry work will be built, without changing a single byte of current single-issue behavior.

Delivered across five founder-certified increments (each: compile → full suite → per-increment hostile
review → byte-for-byte verification → stop-for-certification):

| Inc | Layer | Modules |
|-----|-------|---------|
| 1 | Context object | `scout_context.py` (new) |
| 2 | Read path | `audit_s3_source.py` |
| 3 | Persistence / index / ledger | `scout_report_publisher.py`, `scout_report_index.py`, `scout_revision_ledger.py` |
| 4 | Evidence + runners | `audit_review.py`, `scout_delta_audit.py`, `dataset_auditor.py` |
| 5 | Projections | `scout_benchmark.py`, `scout_archive.py`, `scout_intelligence.py` |

---

## 2. Final execution architecture

ADR-0001 defines four logical layers **Discovery → Registry → Audit → Publication**. Phase 1 implemented the
`IssueContext` seam through the **Audit** and **Publication** layers only; **Discovery and Registry are not
built** (Phase 2).

```
          ┌──────────────────────── edenseek-publishing (Publisher-owned, READ-ONLY to Scout) ─┐
          │  approved/published.json (pointer) · processing_snapshot · reviews/{id}/…           │
          └───────────────────────────────────────────────────────────────────────────────────┘
                                            │  (GET only; IAM Deny on writes)
                                            ▼
   IssueContext ──────────►  audit_s3_source        (read adapter: resolve revision / materialize contract)
   (identity + approved_*                 │
    + scout_* + revision/                 ▼
    trigger/methodology)     audit_review              (evidence manifest + run the deterministic delta)
                                          │                    │
                                          ▼                    ▼
                             ANALYZERS (deterministic, no LLM):
                             review_contract_adapter → delta_geometry (IoU) + delta_metadata_revision
                                          │
                                          ▼
                       RUNNERS: scout_delta_audit.run_and_persist / audit_current_revision
                                dataset_auditor.run_dataset_audit
                                          │
                 ┌────────────────────────┼───────────────────────────┐
                 ▼                        ▼                            ▼
        scout_report_publisher     scout_report_index          scout_revision_ledger
        (immutable history +       (derived projection;        (idempotency authority;
         latest pointer; R1 keys;  comparability; query)        context_fingerprint)
         readback SHA-256 verify)                              
                 └────────────────────────┴───────────────────────────┘
                                          │  (all writes → edenseek-scout ONLY)
                                          ▼
          ┌──────────────────────── edenseek-scout (Scout-owned, READ/WRITE) ──────────────────┐
          │  {issue}/reports/*.json · {issue}/history/*_{seq}.json · report_index.json ·        │
          │  ledger/processed_revisions.json · {issue|series|publisher}/benchmark · benchmark/  │
          └───────────────────────────────────────────────────────────────────────────────────┘
                                          │  (read-only projections)
                                          ▼
                    scout_benchmark · scout_archive · scout_intelligence
                                          │
                                          ▼
        OPERATIONAL SURFACE (unchanged in Phase 1): app.py (FastAPI) · scheduler.py · scout_watch.py ·
        static/index.html — all call the runners/projections with NO context (env default).
```

---

## 3. Layer responsibilities

| Module | Responsibility | Ownership side |
|--------|----------------|----------------|
| `scout_context.py` | Canonical `IssueContext` value object; resolves identity + S3 surfaces; `from_env` / `for_prefixes` / `derive`. **Leaf module** (stdlib only). | — |
| `audit_s3_source.py` | Read adapter for the Approved-Dataset contract: resolve the mutable pointer, materialize + hash-verify the content-addressed revision snapshot. GET-only. | reads Publisher |
| `audit_review.py` | Evidence layer: probe the four consumed objects → Consumed-Evidence Manifest; assemble the read-only audit-review *view* and run the deterministic delta. | reads Publisher |
| `review_contract_adapter.py`, `delta_geometry.py`, `delta_metadata_revision.py`, `delta_auditor.py` | **Analyzers.** Anti-corruption adapter (normalize Publisher shapes) → geometry delta (IoU matching: precision/recall/split/merge/false/missing/spread-missing) + metadata revision-distance classifier. Deterministic; no LLM/vision. | Scout-derived |
| `scout_delta_audit.py` | **Delta runner.** `audit_current_revision` (canonical entry; ledger-guarded, idempotent) → `run_and_persist` (evidence → assemble body → persist → index → mark ledger) as one transaction. | writes Scout |
| `dataset_auditor.py` | **Dataset-quality runner.** Score the materialized dataset; publish the report set + consolidated Scout Report. | writes Scout |
| `scout_report_publisher.py` | R1 persistence: immutable `history/{type}_{seq}.json` first, then latest `reports/{type}.json`; readback SHA-256 verification; run_id idempotency. | writes Scout |
| `scout_report_index.py` | **Derived projection** of persisted reports (`report_index.json`); per-task comparability keys; pure query + metric-series. Rebuildable from history — never a source of truth. | writes Scout |
| `scout_revision_ledger.py` | **Idempotency authority** (`processed_revisions.json`), keyed `(issue, revision, methodology-fingerprint)`. Separate from the index. | writes Scout |
| `scout_benchmark.py` | Weighted benchmark projections (issue/series/publisher/platform), summing numerators/denominators — never averaging rates. Bucket-wide. | writes Scout |
| `scout_archive.py` | Read-only archive projection: index reports + failed ledger runs, newest-first, methodology boundaries. | reads Scout |
| `scout_intelligence.py` | Geometry / Metadata Intelligence contracts (recurring failure modes, version-correlated improvements, weak fields) — advisory only. | reads Scout |
| `scout_schema.py` | Dependency-free JSON-Schema validator for the machine-readable contracts. | — |
| `app.py` / `scheduler.py` / `scout_watch.py` / `static/index.html` | Operational surface (HTTP, scheduled jobs, revision watcher, dashboard). **Unchanged in Phase 1**; all pass no context. | — |

---

## 4. IssueContext execution flow

`IssueContext` is a **frozen** dataclass (immutable). Fields:

- **Identity:** `publisher_id`, `title_group_id`, `series_id`, `issue_id` (the canonical ownership chain).
- **Approved read surface:** `approved_bucket`, `approved_prefix` (ends `/approved`), `approved_region`.
- **Scout write surface:** `scout_bucket`, `scout_prefix` (`publishers/.../issues/{id}`), `scout_region`.
- **Forward-looking (carried, inert in Phase 1):** `revision`, `trigger` (`manual|scheduled|reconciliation|event|certification`), `methodology`, `analyzer_registry`, `schedule`.

Construction:

- **`from_env(env=None, *, revision, trigger, methodology)`** — reproduces the modules' env derivation
  byte-for-byte (same env vars, same `us-west-2` default, same prefix validation/normalization), fail-loud
  on missing/invalid config. **Used by tests and reserved for future activation; not called in the flow.**
- **`for_prefixes(...)`** — build a context from explicit prefixes with the same validation. The seam a
  future Discovery/Registry layer uses to build one context per enumerated issue.
- **`derive(**changes)`** — immutable copy with overrides (e.g. attach a `revision`/`trigger`).

Flow when a context is supplied (future / tests):

```
context ─► runner ─► audit_review (uses context.approved_* to read the Publisher evidence)
                 ─► publish_* / update_index / mark_* (use context.scout_* to write edenseek-scout)
```

Flow **today (production)**: every caller passes `context=None`; each module takes its `else:` branch and
reads `os.getenv(...)` exactly as before. The two paths are proven equivalent.

---

## 5. Current execution pipeline (Publisher → Bridge → IssueContext → Analyzers → Reports → Index/Ledger)

1. **Publisher** publishes canonical facts to `edenseek-publishing`: the `approved/published.json` pointer
   (→ current `published_revision_id`), the content-addressed `processing_snapshot`, and the
   `reviews/{review_id}/{review_report,platform_approval}.json` objects. Publisher emits *facts only*
   (Principle P1).
2. **Bridge** (`publisher_bridge/`) is the governance channel between the Publisher/Platform session and the
   Scout session — architecture RFCs, close-outs, gate signals. It is **out of band** from the runtime data
   path; Scout never reads the bridge at audit time.
3. **IssueContext** resolves the execution scope. Today it is the implicit env default (`context=None` →
   each module's env branch); the object exists and is drivable but is not yet built at entry.
4. **Read adapter** (`audit_s3_source`) resolves the current revision and materializes/verifies the contract
   (GET-only on the Publisher repository).
5. **Evidence + Analyzers** (`audit_review` → `review_contract_adapter` → `delta_geometry` +
   `delta_metadata_revision`) produce the deterministic generated-vs-approved delta + findings. Analyzer
   **applicability is a pure function of the canonical facts** and lives entirely on the Scout side
   (Principle P1): metadata abstains on schema skew; the delta is N/A for a manual publication; dataset
   quality always applies.
6. **Runner** (`scout_delta_audit` / `dataset_auditor`) assembles the versioned, provenance-bearing report
   body, computes the deterministic `run_id` + comparability keys, and executes the persist → index → ledger
   transaction.
7. **Reports** are written to `edenseek-scout` (immutable history first, then latest pointer; readback
   SHA-256 verified). **Index** is updated in the same transaction (derived projection). **Ledger** is marked
   processed **only after** all verified persistence steps succeed. Everything is read-only/advisory —
   Scout never approves or mutates Publisher data (Charter §4).

---

## 6. Remaining `from_env()` behavior and why it still exists

There are two distinct environment-reading mechanisms after Phase 1, and this is deliberate:

- **(a) Per-module `context=None` branches — the live production path.** Each threaded function keeps its
  original `os.getenv(...)` + prefix-validation block verbatim inside an `else:`. This is what runs in
  production today. It was **not** rerouted through `IssueContext.from_env()` on purpose, to preserve the
  exact fail-loud exception *types* (`ScoutS3SourceError` / `ScoutReportPublishError` — on which the
  `app.py` `→ 503` handler and existing tests depend) and to avoid requiring the *write* env for a
  read-only operation.
- **(b) `IssueContext.from_env()` — reserved for activation.** It reproduces mechanism (a)'s derivation
  byte-for-byte but raises `IssueContextError` and requires both surfaces. It is currently exercised **only
  by tests**; it is the future single entry that a runner will call once (`context = context or
  from_env()`) to build the context at the top of the flow and thread it down.

**Why it still exists:** `from_env()` is the migration bridge between today's implicit env-based single-issue
configuration and the explicit context object. Keeping both mechanisms lets the certified system run
unchanged (mechanism a) while the context object is fully wired and test-proven (mechanism b), so
**activation** — flipping the runners to `context = context or from_env()` and eventually deleting the
per-module `else:` branches — becomes a small, isolated, separately-certified increment rather than a
big-bang switch.

---

## 7. Architectural invariants future work MUST preserve

1. **Repository ownership (ADR-0001 D1).** Scout writes **only** `edenseek-scout`; reads `edenseek-publishing`
   read-only; IAM Deny enforces it. No code path may write the Publisher repository.
2. **Facts vs. observations (Principle P1).** Publisher emits facts; Scout derives observations and
   **analyzer applicability** (a pure function of canonical facts, resolved in Scout's analyzer registry).
   The Publisher stays analyzer-unaware; Scout never becomes authoritative for Publisher state.
3. **`context=None` ≡ env path, byte-for-byte** — until activation is separately certified. Any change to a
   `context=None` branch must be proven byte-equivalent.
4. **Ledger is the idempotency authority (D4).** `run_id` is a deterministic hash over
   `published_rev | generated_rev | geometry_key | metadata_key`; the same publication under the same
   methodology fingerprint must reconcile, never duplicate. No second path may bypass the ledger.
5. **Index is a derived projection (D3)** — rebuildable from immutable history, never a source of truth.
6. **Immutability + verification.** History objects are append-only and never overwritten; every write is
   readback SHA-256 verified; the latest pointer is byte-identical to its history snapshot.
7. **Comparability discipline.** A methodology-version change mints new comparability keys / fingerprint and
   marks a boundary; benchmarks sum numerators/denominators and **never average rates**; every point carries
   sample size and dual event/measurement time.
8. **`IssueContext` is a leaf + immutable.** No Scout module may create an import cycle back into it; it must
   stay a frozen value object.
9. **Fail-loud.** Misconfiguration raises; Scout never silently audits or writes the wrong issue.
10. **Read-and-advise only (Charter §4).** Reports are advisory; Scout never approves/rejects/locks/mutates,
    never becomes the source of truth, never bypasses human approval.

---

## 8. Recovery guarantees and rollback point

- **Rollback point:** pre-merge `main` @ **`b24d058`**. The Phase 1 merge is `fe07303`.
- **Pre-deploy rollback (current state):** the VM still runs the pre-Phase-1 code — Phase 1 is **not
  deployed**. To abandon Phase 1, `git revert` the merge commit `fe07303` on `main`; production is
  unaffected either way.
- **Post-deploy rollback (if Phase 1 is ever deployed):** `git checkout b24d058` on the VM +
  `sudo systemctl restart edenseek-scout` returns to the certified single-issue behavior. Rollback is
  **code-only** — `.env` and IAM are unchanged by Phase 1.
- **Data safety:** Phase 1 wrote nothing new or irreversible. The immutable reports / index / ledger are
  unchanged; the production re-cert reconciled (skipped) rather than writing. Any accidental write to
  `edenseek-scout` is S3-versioned and recoverable, and can never reach `edenseek-publishing` (IAM Deny).
- **Idempotency guarantee:** re-running the canonical entry on an already-processed revision under an
  unchanged fingerprint returns `skipped` with no new `run_seq` (verified live).

---

## 9. Extension points for Phase 2 and beyond

`IssueContext` was designed as the substrate for the remaining ADR-0001 layers. Each future capability
attaches at a named seam **without** changing certified single-issue behavior:

- **Discovery.** Enumerate issues to audit. A bucket-wide scan already exists in embryo
  (`scout_benchmark.discover_issue_indexes` lists every per-issue index under `publishers/`). A Discovery
  layer generalizes enumeration (from the Publisher surface / a manifest), yielding a set of identities.
  **Seam:** build one context per enumerated issue via `IssueContext.for_prefixes(...)`.
- **Registry.** A **derived projection** of per-issue state resolved from canonical objects
  (`approved/published.json` = revision; `reviews/{id}/platform_approval.json` presence = state) — **never**
  the stale Publisher `dataset_registry.json` (D3). Entries carry the full flat hierarchy (D6); the tree is
  a rollup view. **Seam:** a new `scout_registry.py` leaf/projection consuming contexts + index/ledger.
- **Scheduler.** `IssueContext.schedule` (inert field). `scheduler.py` would enumerate via Discovery, build
  contexts, and run the canonical entry per issue on cadence. **Seam:** activate `from_env()`/`for_prefixes`
  at the scheduler entry; the runners already accept `context`.
- **Analyzer Registry.** `IssueContext.analyzer_registry` (inert field). The two audit entry points
  (dataset-quality + delta) converge into **one revision-oriented analyzer-registry Audit** where each
  analyzer decides its own applicability from canonical facts (`applicability = analyzer(facts) →
  run|abstain|not_applicable`). **Seam:** the Audit layer orchestrates registered analyzers over a context.
- **Autonomous operation (Charter Stage 4).** The context is the unit of work a future research/critic/
  strategist/publisher agent loop would operate over. Far future; no design commitment here.

**Activation (prerequisite for most of the above):** flip the runner entries to
`context = context or IssueContext.from_env()`, then (later) retire the per-module `context=None` env
branches. This must be its own certified increment (see §6).

---

## 10. Risks and assumptions entering Phase 2

**Assumptions (true today; must be re-validated if they change):**
- The production `SCOUT_APPROVED_S3_PREFIX` carries the full `series/issues` identity (required by the
  dataset-audit path today; `from_env` cross-checks approved vs scout identity).
- Both S3 surfaces are in `us-west-2`; a single client region serves reads + writes.
- Single-issue operation — exactly one certified issue (`issue_001`) is live; the "tree" is a tree-of-one.
- The Publisher platform is **FROZEN** and holds Scout code; the three optional Publisher enhancements
  (approved-revision event; wire `dataset_registry.json` to the 6.2 state machine; hierarchy/health
  manifest) are **Gate-C-gated and are not Phase-2 dependencies**.

**Risks / open items:**
- **Activation divergence.** `from_env()` requires *both* surfaces and raises `IssueContextError`, unlike the
  per-module env branches. Activation must reconcile exception semantics (esp. the `→ 503` handler) — do it
  as an isolated certified step.
- **Discovery scale.** `discover_issue_indexes` scans the whole bucket under `publishers/`. Fine at current
  scale; a large multi-issue platform will want pagination/indexing discipline (log any cap; no silent
  truncation).
- **Cross-process concurrency.** Memory/locking is in-process only; cross-process safety awaits the SQLite
  migration (existing tech debt). Multi-issue scheduled operation may surface this before SQLite lands.
- **Registry-as-projection discipline (D3).** The Registry must be strictly derived and rebuildable; any
  temptation to treat it (or the Publisher `dataset_registry.json`) as a source of truth is a boundary
  violation.
- **Two entry points still separate.** Until the analyzer-registry convergence, dataset-quality and delta
  remain distinct triggers; keep them behaviorally frozen until that design is certified.

---

## 11. Certification record

- **Increments 1–5**, each independently founder-certified; per-increment hostile reviews under
  `docs/phases/phase-1-issuecontext/`.
- **Final hostile-review checklist:** `docs/phases/phase-1-issuecontext/PHASE_1_HOSTILE_REVIEW_RESULT.md`
  (PASS).
- **Full test suite:** 260 passed, 0 failures (venv `unittest`).
- **Production re-cert (live):** dry-run reproduced `run000003` (`run_id run_833dfc915be60481`, comparability
  `cmp_5a84e2667714` / `cmp_2d1ab97056d5`, fingerprint `fp_580cbeb1f41b`); canonical entry returned
  `skipped` (idempotent, no new `run_seq`); read-only, no `edenseek-publishing` writes.
- **Merge:** PR #2 → `main` `fe07303`. **Rollback:** `b24d058`. **Not deployed to the VM.**

**Phase 2 (Discovery → Registry) begins from this certified baseline on explicit founder go-ahead.**
