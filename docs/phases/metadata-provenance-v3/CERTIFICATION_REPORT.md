# Certification Report — Metadata Accuracy v3 (revision-aware acceptance denominator)

**Track:** Week 12 · Metadata Provenance Interface (revision-aware)
**Branch:** `week12-metadata-v3-revision-aware`
**Date:** 2026-08-11
**Discipline:** certified-first (build → adversarial review → certify → deploy → live-cert, each separate)
**Status:** CODE-COMPLETE · adversarially reviewed (1 round + verification) · offline-certified · HELD for merge → deploy → coordinated rev-2 live cert

---

## 1. What changed and why

v2 measured acceptance over **fresh outputs only**, keyed on the per-artifact
`metadata_generation_provenance` flag (`fresh` vs `preserved_*`). That is correct on a **first
publication**. On a **revision** it is not: metadata is *inherited*, but the inherited output keeps
its **original** `metadata_generation_provenance` — so a rev-1 `fresh` output still reads `fresh` in
rev 2 even though **no LLM ran this revision**. v2 would admit those carried-forward outputs into the
denominator, diff them to zero (byte-identical inheritance), and report another editorially-meaningless
`rate = 1.0`.

v3 makes the acceptance denominator **revision-aware**: it counts only content an LLM actually produced
**this revision**, discriminated by the Publisher `origin` field.

**The discriminator is the PRESENCE of `origin`, not its value** — established from live Publisher
evidence (`publisher_bridge/2026-08-11_publisher_origin_field_shapes_and_a_correction_to_the_planned_filter.md`,
§1): `origin` is written **only** on the revision-inheritance path, and is **absent on 100/100 outputs of
a first publication**. The earlier planned rule (`origin ∈ {generated, regenerated}`) would have zeroed
the denominator on every first publication — caught by Johnny before build.

This is a **metric-vocabulary evolution**, not a content or workflow change. Scout remains an independent
read-only auditor; Publisher authority and approved-dataset semantics are untouched.

## 2. The acceptance predicate (authoritative)

```python
def _counts_toward_acceptance(r):
    if not r.get("generated_has_origin"):        # generation path (first pub, or in-revision regen)
        return r.get("generated_disposition") in (None, "fresh")   # ← byte-identical to v2
    return r.get("generated_origin") in ("generated", "regenerated")   # revision-inheritance path
```

Truth table (over every case the Publisher can currently produce — bridge §2):

| case | `origin` | `mgp` | counts? |
|---|---|---|---|
| first publication, generated | absent | `fresh` | ✅ (generation branch) |
| first publication, preserved | absent | `preserved_approved` | ❌ |
| revision, inherited, unreviewed | `carried_forward` | inherited (may say `fresh`) | ❌ |
| revision, inherited, re-approved | `confirmed` | inherited (may say `fresh`) | ❌ **(the trap)** |
| revision, editor regenerated a panel | expected absent | `fresh` | ✅ (generation branch — handled either way) |
| revision, added / split / merged | `null` (present) | absent | ❌ (empty class) |

The generation branch **is literally the v2 filter**, so every prior report is byte-stable (§4).

## 3. Scout-side changes (this branch)

- **`review_contract_adapter.py`** — `_normalize_metadata` canon entry carries two additive keys per
  artifact: `origin` (`out.get("origin")`) and `has_origin` (`"origin" in out`). Presence vs
  present-and-null are distinguished by `has_origin`, never conflated. `origin` is an enum/None — no raw
  text, deterministic.
- **`delta_metadata_revision.py`**
  - `METADATA_ACCURACY_VERSION` `v2 → v3`.
  - `_counts_toward_acceptance` (new) — the shared acceptance predicate, used at **both** filter sites
    (`_metadata_accuracy` `is_fresh` and `compute_metadata_benchmark` `_fresh`) as the *same function
    object*, so the headline and the accuracy block cannot diverge.
  - Each record carries `generated_origin` and `generated_has_origin`.
  - `denominator_basis` → `"llm_generated_this_revision_only"`.
  - **Coverage gate made revision-aware** (the adversarial-review fix, §7) — `disposition_coverage` /
    `provisional` are now computed over **generation-path records only** (`origin` absent). Revision-
    inheritance outputs (incl. the empty add/split/merge class, which legitimately carries no disposition)
    no longer count toward the "partial emission" check.
  - `low_confidence_no_inspection` (new, advisory) — `True` when `comparable > 0 AND rate == 1.0 AND
    total_edited == 0`. A proxy for "approved without per-artifact inspection" (e.g. bulk Approve-All).
    **Does not touch `meets_target`** (Publisher-endorsed, bridge §6); interim until the post-Week-12
    bulk-approve signal.
  - `meets_target = None` whenever `provisional` **or** `comparable == 0` (a 0-denominator revision — an
    editor who regenerated nothing — is the *correct* answer, withheld, never a false pass).

## 4. Backward compatibility (proven)

On a first publication `origin` is absent on every output, so **both branches collapse to the v2
predicate** `disposition in (None, "fresh")`. v3 is therefore **numerically identical** to v2 on all data
audited so far, including the jointly-certified `i_ride_for_them` #1 rev 1 (fresh × 65 / preserved × 35 →
the same 384-field fresh denominator, 193 excluded, `disposition_coverage: all`). Regression tests assert
number-identity on origin-absent fixtures; the changed strings (`denominator_basis` label) are descriptive,
not comparability axes or numbers.

## 5. Version / comparability / idempotency

`metadata_accuracy_version` is in **both** the comparability axis (`scout_report_index` `METADATA_AXES`
+ `metadata_axes`, lines 45/89) **and** the ledger fingerprint (`scout_delta_audit.static_versions()`,
line 51). v2→v3 therefore (a) changes the fingerprint → the re-audit **runs** (no skip) and (b) changes
the `metadata_comparability_key` → the `run_id` changes → **no collision** with the certified v2 run. The
dual-condition is satisfied by construction (verified in the review, claim #7).

## 6. Tests

Full suite **452 passed**. New: `tests/test_metadata_v3_origin.py` (11 tests) — version/basis; first-pub
origin-absent counts (v2-identical); the `confirmed`+`fresh` trap excluded; `carried_forward` excluded;
empty-class `origin:null` excluded; hypothetical `generated`/`regenerated` counted; mixed generation/
inheritance; zero-denominator all-inherited is correct-not-failure; low-confidence marker true/false;
**empty-class does not trigger false partial coverage** (the §7 regression). Updated:
`tests/test_metadata_revision.py` (record-key allowlist + v2→v3), `tests/test_metadata_v2_contract.py`
(`denominator_basis`).

## 7. Adversarial review (one round + verification)

An independent reviewer traced every concern against source and the authoritative Publisher bridge doc.
The two highest-risk claims — **backward-compat** (number-identical) and **two-site consistency** — were
verified SOUND. It found **one MAJOR latent gap**, now fixed and regression-tested:

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MAJOR (latent) | The `provisional`/`disposition_coverage` gate was left keyed on `generated_disposition` presence, not made revision-aware. A **mixed revision** — an in-revision regenerated output (flagged) **plus** an empty add/split/merge output (`origin:null`, no disposition → `generated_disposition=None`) — read as `coverage="partial"` → `provisional=True` → `meets_target=None`, falsely **withholding** a legitimate verdict on exactly the revision v3 exists to serve. Conservative (never a false green) and impossible today (needs an in-revision regeneration *and* an add in the same revision — never co-occurred), hence latent. | Coverage/`provisional` now computed over **generation-path records only** (`origin` absent); revision-inheritance outputs (incl. the empty class) are excluded from the "partial emission" check. Regression test `test_empty_class_does_not_trigger_false_partial_coverage`. |

Claims the reviewer tried and could not break: presence-vs-present-null discriminator never confused;
backward-identical on first publications; the two filter sites are the same predicate; zero-denominator →
`meets_target=None`; version wired in both the fingerprint and the comparability axis; adapter additive /
no raw-text; `low_confidence_no_inspection` computationally exact and advisory-only.

Nits (accepted, not defects): `excluded_preserved_artifacts` is a slightly-legacy name now that the set
also includes origin-excluded artifacts (the set membership is correct; renaming would churn the contract
Johnny verified for `i_ride_for_them`); `denominator_basis` string change appears only on a fresh v3 run.

## 8. Certification statement

The change is additive and backward-compatible (number-identical on all data audited to date),
deterministic, stores references/enums only (no raw text), preserves Publisher authority and Scout's
read-only boundary, and communicates a metric-vocabulary evolution (`METADATA_ACCURACY_VERSION v3`) via
both the comparability axis and the ledger fingerprint. The one MAJOR latent gap surfaced by adversarial
review is fixed and regression-tested. **Offline-certified.** Remaining gates: merge → deploy
(`SCOUT_RUNTIME_MODE=production`) → coordinated **rev-2 live certification** on `i_ride_for_them` #1 rev 2
(currently held by the Publisher pending this build), where the denominator should reflect only what an
LLM produced in that revision — legitimately **0 comparable fields** if the editor regenerates nothing.
