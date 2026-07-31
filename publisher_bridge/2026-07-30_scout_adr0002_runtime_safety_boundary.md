# Scout → Publisher bridge: ADR-0002 (Runtime Safety Boundary) — platform-wide adoption

**Date:** 2026-07-30 · **From:** Scout session · **To:** Publisher/Platform session · **Type:** architectural rule (founder-directed, platform-wide)

## What happened (Scout side, contained)

A local Scout test-suite run on a workstation whose `.env` held live credentials constructed a
**real** production S3 client through an unmocked `client=None` fallback and published an
uncertified report to `edenseek-scout`. Caught immediately; active state restored; no Publisher data
touched. Full incident + RCA: `docs/phases/geometry-correctness/PRODUCTION_WRITE_INCIDENT.md`.

## The rule the founder has established (binding, platform-wide) — ADR-0002

> **Production access must never be reachable by test code through ambient credentials alone.
> Production operations must always require an explicit, intentional execution mode enforced by the
> runtime.**

Full record: `docs/architecture/ADR-0002-runtime-safety-boundary.md`. The founder wants this to be a
permanent architectural rule for the **entire Edenseek platform** — future Publisher services and AI
agents inherit the boundary by design.

## Ask of the Publisher/Platform session

Adopt the same boundary in Publisher services that touch cloud resources:

1. An explicit **runtime mode** signal (production / development / test).
2. **Deny-by-default** for non-production processes (real clients only with an intentional opt-in).
3. A **single guarded factory** per resource — the only path that constructs a real client, gated
   on the runtime mode. No second path.
4. **Test harnesses default to fakes** and can never reach production, even with ambient credentials.
5. **Production is opt-in at deploy time** (an explicit mode/flag); deploying without it fails safe.
6. **CI verifies** a test process cannot construct a real client.

Scout's implementation is a reusable reference (`scout_runtime.py` + two guarded factories +
`tests/__init__.py` + `tests/test_production_safety.py`). No Scout-side dependency on the Publisher;
this is a shared-principle adoption, tracked as a platform obligation in ADR-0002.
