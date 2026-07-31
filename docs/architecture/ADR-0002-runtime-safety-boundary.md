# ADR-0002 — Runtime Safety Boundary: production access requires an explicit, enforced execution mode

**Status:** ACCEPTED (founder-directed, 2026-07-30).
**Deciders:** founder; Scout session. **Originating event:** an accidental production write during
local test execution (`docs/phases/geometry-correctness/PRODUCTION_WRITE_INCIDENT.md`).
**Scope:** **platform-wide** — every Edenseek service and AI agent that can reach cloud resources
(Scout, future Publisher services, future agents). First implemented in Scout (`scout_runtime.py`).

---

## Context

A full Scout test-suite run, executed on a workstation whose `.env` carried live credentials,
constructed a **real** production S3 client through an unmocked `client=None` fallback and published
an uncertified report to the production bucket. No data was lost and it was caught immediately, but
it exposed a structural weakness: **the only thing standing between test/development code and
production was a convention** ("remember to inject a fake client"). Ambient credentials — from
`.env`, `~/.aws`, or an instance role — were sufficient to reach production from any process that
imported application code.

The problem was not the mistake; it was that the environment *allowed a production client to be
constructed at all* from a non-production context.

## Decision (the principle — binding, platform-wide)

> **Production access must never be reachable by test code through ambient credentials alone.
> Production operations must always require an explicit, intentional execution mode enforced by the
> runtime.**

Enforcement model (every service/agent inherits this by design):

1. **Explicit runtime mode.** A single environment signal (`SCOUT_RUNTIME_MODE` in Scout; the
   platform equivalent elsewhere) with values `production` / `development` / `test`.
2. **Deny-by-default.** The default (`development`) refuses real cloud clients unless an explicit,
   intentional opt-in is set (`SCOUT_ALLOW_REAL_S3=1`). Unset/unknown ⇒ development ⇒ deny.
3. **A single guarded choke point.** Real cloud clients are created in exactly one factory per
   resource, and that factory consults the runtime mode before constructing anything. There is no
   second path.
4. **Tests default to fakes and can never reach production.** In `test` mode the factory *always*
   refuses; the test harness forces this before any application import; and because the default
   already denies, tests are safe even if the harness bootstrap does not run.
5. **Production is opt-in at deploy time.** The deployed agent runs with the production mode set
   explicitly (a deployment flag), never by accident. Deploying the guard without setting production
   mode fails safe (the agent is denied) rather than fails open.
6. **CI verifies the boundary.** A standing test asserts that a test process cannot construct a real
   client — the boundary is regression-guarded, not documented-and-forgotten.

## Consequences

- **Positive:** the entire class of "development/test code silently touches production" failures is
  eliminated by construction, not vigilance. Reinforces the existing immutability posture (Scout's
  write identity already lacks `s3:DeleteObject`; this ADR adds an intentional-mode gate on top).
- **Cost:** every real cloud entry point must route through the guarded factory; deployments must
  set production mode explicitly; intentional local/recovery operations must opt in. These are
  deliberate frictions on production access, which is the point.
- **Platform obligation:** future Publisher services and AI agents must adopt the same boundary
  (their own `RUNTIME_MODE` + guarded factories + deny-by-default). Communicated to the Publisher
  session via `publisher_bridge/`. This ADR is the durable, platform-level rule; per-service
  implementations are the mechanism.

## Scout implementation (reference)

`scout_runtime.py` (the gate: `guard_real_s3_client`, mode resolution, `ScoutSafetyError`);
`audit_s3_source._s3_client` + `scout_report_publisher._s3_client` (the two guarded factories);
`tests/__init__.py` (forces `test` mode + bogus creds); `tests/test_production_safety.py` (CI guard).
The deployed VM must set `SCOUT_RUNTIME_MODE=production`.
