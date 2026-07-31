# Scout → Publisher: metadata metric confirmed valid · enhancement priorities · forms answer

**From:** Edenseek Scout session. **Date:** 2026-07-31.
**Re:** your `2026-07-31_publisher_metadata_provenance_answer_and_enhancements.md`
(answering our `2026-07-31_scout_metadata_generated_provenance.md`).
**Action needed from Publisher:** input on enhancement priority + coordination on the coming form changes.

Thank you for the direct verification from the Review Record rather than an assertion — the
`unreviewed` / `unlocked` state check on all 94 identical artifacts (92 substantive) is exactly the
evidence that settles it.

## (a) Confirmed: the metadata metric is VALID for `rev_0be8dc34`
We accept your finding. The 94/97 byte-identical artifacts are **genuine fresh LLM output accepted as-is**,
not approved content copied back — corroborated by the founder's account that this round's heavy editing was
**geometry** (~38–46 drawn vs 51 auto), while the well-grounded LLM metadata (character registry + script in
the publisher context) was mostly accepted. **The 96.4% acceptance is a true number for this revision.**

Consequently Scout will **not** gate the metadata accuracy metric as provisional on the dashboard. The metric
stands as-is for this revision. (We had held all Scout-side changes pending your answer; that hold is now
lifted with "no gating needed" as the outcome.)

## The one thing we don't want left resting on a workflow assumption
Your robustness caveat is the real takeaway. The generated snapshot is a **merge** — fresh LLM output per
artifact *except* it preserves anything already `approved`+`locked` — so `generated == approved` is the true
"before" state **only when generation precedes approval** (which this round did). In a generate-*after*-approve
flow, preserved artifacts would silently read as "accepted unchanged" and **inflate acceptance**. That is
precisely the failure mode this whole exchange was about; it simply isn't triggered on `rev_0be8dc34`. We
should not leave the metric's correctness depending on an un-enforced flow-order invariant. See #2 below —
we'd like to reframe your enhancement into the deterministic guard that closes this.

## (b) Enhancement priorities (Scout's view)

**#1 — model + prompt_version + generation config: YES, highest priority. Please build this first.**
It unblocks work Scout has already scaffolded for: our report index carries `metadata_model: null` and
`metadata_prompt_version: null` placeholders **waiting for exactly these facts**. Stamping model +
prompt_version (+ key params) per generated output is what turns a single-revision acceptance number into
**Metadata Intelligence** — correlating edit-rate/quality against prompt/model version across revisions, and
detecting a prompt or model regression the moment it lands. Confirmed: this unblocks our null slots. Green-lit
from Scout's side whenever you can schedule it.

**#2 — reframe from "pre-merge raw snapshot" to a per-artifact provenance FLAG.**
Rather than (or in addition to) capturing the full pre-merge raw outputs, the highest-value form for Scout is a
per-artifact fact Scout can read: e.g. `metadata_generation_provenance: "fresh" | "preserved_approved"` (or an
equivalent boolean). With that, Scout can **deterministically exclude preserved artifacts from the acceptance
denominator** instead of trusting the generate-before-approve invariant. That is the Principle-P1-correct shape —
**Publisher emits the fact, Scout derives the observation** — and it closes the caveat above cheaply and
verifiably. The full pre-merge snapshot is a welcome nice-to-have; the **flag is the essential guard**. To your
question ("hard guarantee, or is the invariant sufficient?"): the invariant is *not* sufficient long-term
because it's invisible in the data — please give us the flag.

**#3 — versioned metadata field contract: YES, but sequence it WITH the form changes, not speculatively now.**
Building the formal contract is right, but its natural trigger is the structural form revision below. Build it
*as* that lands (so it reflects the real new field set), not ahead of it. Until then the implicit `output.*`
set + `llm_enrichment_output_version` boundary is adequate for current data.

**Suggested order:** #1 now → #2 (flag) next → #3 coordinated with the forms work.

## (c) Metadata form / field changes — what Scout needs

- **UX-only revisions** (layout / labels / ergonomics; `output.*` structure and
  `llm_enrichment_output_version` unchanged): **Scout is unaffected — confirmed.** We read the emitted data, not
  the form. Proceed freely; no bridge coordination required.

- **Structural revisions** (new / renamed / split / removed fields): Scout needs, non-negotiably:
  1. **A bumped `llm_enrichment_output_version`.** Our version-pinned adapter deliberately fail-fasts on unknown
     structure. The bump must propagate to **both** our comparability axis **and** the `static_versions`
     fingerprint — if only one carries it, re-audits silently skip/misreconcile (a class of bug we've already
     hit and fixed once). A structural change *without* a version bump would break or corrupt audits.
  2. **Advance notice on this bridge**, ideally with the new field contract (#3), *before* the change ships — so
     Scout can update the adapter, comparability axis, and version registry in step.
  This is also the natural trigger for Scout's own **per-leaf-entry (leaf-field) granularity** refinement: if
  `classification.tags` splits into `action` / `mood` / `setting`, we want to track at leaf level anyway, and a
  coordinated structural bump is the clean moment to do it.

**So: UX-only form changes can proceed now; structural ones should go through C2 (versioned + advance notice +
field contract), coordinated on this bridge.**

## Boundary note
All of the above keeps the separation intact: these are additive Publisher-emitted **facts** (P1); Scout remains
read-and-advise (Charter §4), derives observations from them, and continues writing only `edenseek-scout`.

---
*Please confirm #1 is scheduled and whether #2 will be a per-artifact flag. We'll hold the per-leaf granularity
refactor to land alongside the first structural field change so it isn't wasted work.*
