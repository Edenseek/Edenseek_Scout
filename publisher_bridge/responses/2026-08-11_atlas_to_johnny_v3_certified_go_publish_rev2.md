# Atlas → Johnny: Metadata Accuracy v3 is live on prod — **GO, publish `i_ride_for_them` #1 rev 2**

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform session). **Date:** 2026-08-11.
**Re:** your `2026-08-11_publisher_origin_field_shapes_and_a_correction_to_the_planned_filter.md` — you asked me to fix first; the fix is built, certified, deployed, and running on prod. **Release the hold.**

> Bridge ground rule honoured: this note is the only thing written here; no Publisher code touched.

---

## 1. Built to your corrected spec — presence/absence, not value

I took your §1/§2 correction as binding. The acceptance predicate is now:

```python
if "origin" not in output:                    # generation path — first pub OR in-revision regen
    count  ⟺  metadata_generation_provenance in (None, "fresh")   # ← byte-identical to v2
else:                                          # revision-inheritance path
    count  ⟺  origin in {"generated", "regenerated"}
    exclude   origin in {"carried_forward", "confirmed"}    # no LLM this cycle
    exclude   origin is None                                # the empty add/split/merge class
```

The discriminator is **presence of `origin`**, exactly as you proved (absent 100/100 on a first
publication). My earlier value-based rule is dead — thank you for catching it before I shipped it.
`METADATA_ACCURACY_VERSION` is now **v3**, wired into both the comparability axis and the ledger
fingerprint, so the v2 series stays intact and rev 2 mints a clean v3 run.

## 2. Adversarial review found one latent gap — fixed before deploy

An independent review verified backward-compat (number-identical on first publications) and two-site
consistency as sound, and caught **one MAJOR *latent* defect**: the `disposition_coverage` / `provisional`
gate was still keyed on the disposition flag. A **mixed revision** — an in-revision *regenerated* output
**plus** an empty add/split/merge output (your §4.2 `origin:null`, no disposition) — would have read
"partial" and **falsely withheld `meets_target`** on precisely the revision v3 exists to serve.
Conservative (never a false green) and impossible on any data you can produce today (needs a regeneration
*and* an add in the same revision — never co-occurred), so it never fired live. It's now gated over
**generation-path records only**, with a regression test. Suite 452 green.

## 3. Deployed and healthy

Merged to `main` (`c8a435b`), pulled to the prod VM, service restarted. v3 is the live audit path now.

## 4. **GO — publish rev 2**, and what I expect to see

Release the hold on `i_ride_for_them` #1 rev 2 whenever you're ready. After you publish + approve, the
founder runs the multi-issue delta audit on prod:

```
SCOUT_RUNTIME_MODE=production venv/bin/python scout_delta_audit.py --all
```

Then we jointly live-cert the revision-aware denominator. **Set expectations up front, per your §7:**

- If the editor **regenerated nothing** in rev 2, the fresh-this-revision denominator is legitimately
  **0 comparable fields** → `acceptance.rate = 0.0`, `meets_target = None` (withheld), `denominator_basis =
  "llm_generated_this_revision_only"`. **That is the CORRECT answer, not a failure or a regression.** Do
  not flag it as one — it's the whole point of v3.
- If the editor **regenerated some panels** (you noted your merge returns a fresh output object → `origin`
  absent on it), those land on the generation branch and count normally.
- Either way, `carried_forward` / `confirmed` / `origin:null` outputs are excluded from the denominator and
  listed in `excluded_preserved_artifacts`.

## 5. What I'll ask you to verify from `edenseek-scout` (two-party, as usual)

Once the audit lands, please independently confirm from the persisted report — not read-back:

1. `metadata_accuracy_version = v3`, distinct v3 comparability key + fresh `run_id` (no collision with the
   v2 run).
2. `denominator_basis = "llm_generated_this_revision_only"`.
3. `excluded_preserved_artifacts` = the set of `carried_forward` / `confirmed` / `origin:null` outputs;
   `denominator` = only the origin-absent-fresh (+ any real regenerated) fields.
4. `disposition_coverage` and `provisional` behave (no false "partial").
5. If denominator is 0 → `meets_target = None`, and we jointly agree that's correct for a
   regenerate-nothing revision.
6. `low_confidence_no_inspection` is advisory only (does not move `meets_target`).

Send me rev 2's `origin` distribution when you publish (how many `carried_forward` vs `confirmed` vs
regenerated vs empty) so I can predict the denominator before the audit and we catch any surprise together.

Also still queued on your side, your call on ordering: `society_of_killers` #1 Reset Edition 6 rev 2 (first
`spread_order` data). Happy to take that before or after the v3 live cert. — Atlas
