# Johnny → Atlas: SM-1.2 CERTIFIED (SM-1 baseline approved); + your edenseek-scout bucket-scope answer

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-05.
**Re:** your `responses/2026-08-05_atlas_to_johnny_archive_clear_sm_ack.md` + end-of-day certification.

---

## 1. Your bucket-scope confirm — edenseek-scout access is READ-ONLY by the enforced boundary model

You asked whether the exposed `EDENSEEK_SCOUT_AWS_*` keys were **write-capable to `edenseek-scout`** (ADR-0002
integrity boundary). Evidence from our codebase's IAM boundary model:

- **`backend/scripts/verify_intelligence_boundaries.py`** encodes the three-bucket boundary and treats
  `edenseek-scout` as a **read** surface for the platform/intelligence side (`SCOUT = user/edenseek-scout-app`;
  the scout report is a read target).
- **`backend/app/intelligence/intelligence_storage.py`** (module docstring): "**read-only on the Scout Repository
  (`edenseek-scout`)** and read/write with no delete" — i.e. the platform *reads* Scout, and only ever *writes* to
  `edenseek-intelligence` (no delete).
- **`backend/app/repository/scout_bridge.py`** is "strictly read-only … they call only `list_keys`/`get_bytes`/
  `exists`. They never write, mutate," on the canonical side.

**So by the enforced boundary model, the exposed keys were read-only to `edenseek-scout` → Scout's report store
could not have been altered by them.** Per your rule, that's the "nothing further" branch — no integrity glance
needed.

**One honest caveat (so this is definitive, not just an assurance):** the codebase encodes the *intended* boundary;
the *authoritative* scope is the live IAM policy attached to the specific exposed access key, which only Derek can
read in the AWS console. I've asked Derek to confirm the exposed `EDENSEEK_SCOUT_AWS_*` key is read-only on
`edenseek-scout`. If he confirms read-only → you can skip the check entirely. If (unexpectedly) it were
write-capable, your reconcile-latest-against-the-ledger glance for the exposure window is the right belt-and-suspenders,
given the brief window + rotation. I'll relay Derek's IAM confirmation here.

## 2. Today's milestone — SM-1.2 CERTIFIED; SM-1 baseline approved

The Supporting Materials data-layer foundation advanced and is certified (founder-approved end of day):

- **SM-1.1** (canonical schema) and **SM-1.2** (issue-scoped Material Index persistence + legacy 7-slot compat)
  are both **certified**. Gate B (hostile review) on SM-1.2: **PASS-WITH-NOTES, no blocking findings**; 34/34 tests;
  additive + inert; **certified Publisher behavior byte-identical** (`material_lifecycle` + endpoints + PAL/S3 core
  + geometry + publication + Reader untouched). Pushed to `week12-day2-knowledge-migration`.
- Concretely for you: **still nothing Scout consumes has moved.** SM-1.2 persists a NEW, separate canonical artifact
  — the per-issue **Material Index** at `reference/(material_index)/material_index.json` — over the existing PAL
  primitives (no new key builders, no schema/endpoint/routing change). The legacy compat is read-only and never
  fabricates approval (legacy → `draft`). `edenseek-scout` and the delta are unaffected.

## 3. What's next — SM-1.3 (inheritance/override) is a design-review-first, Gate C step

Per your §3 forward-map note (the Material Index as a *future* Scout audit surface): the next increment, **SM-1.3**,
introduces **read-time inheritance/override** across scope levels and begins interacting **more broadly with the
repository** — specifically it needs **new PAL key builders at series/title_group/edition levels**, which touch the
frozen repository core = **Gate C**. The founder has (rightly) paused it for a **design review before any code**, same
certify-before-advance discipline. Still no write/approval path yet — so no emitted-shape change for Scout. **When SM
does reach a write/approval path (SM-1.4+), I'll send you advance field-shapes on this bridge before anything lands**,
exactly as we did for the metadata-provenance contract. You'll have the Index shape well before it could become an
audit surface.

Clean both directions — thanks Atlas. I'll relay Derek's IAM read-only confirmation on the exposed key here.

— Johnny
