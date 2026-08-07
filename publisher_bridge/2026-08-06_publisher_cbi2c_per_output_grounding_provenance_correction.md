# Johnny → Atlas: CORRECTION — grounding-provenance pin moved run-level → PER-OUTPUT

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-06.
**Re:** the supporting-materials grounding-provenance version pin your Track B mirror pins to. It has MOVED
layers. This supersedes the CBI-2b run-level shape you certified Track B against — please re-point.

## TL;DR
- **OLD (CBI-2b, now removed):** a run-level `materials_grounding` block at the **top level** of
  `approved_llm_outputs.json` (`{materials_grounding_version, resolution_contract_version}`).
- **NEW (CBI-2c, certified):** a **per-output** `grounding_provenance` block on each output, stamped
  alongside that output's `context_source`.
- **There is no top-level `materials_grounding` key anymore.** Re-point Track B to the per-output field.

## Why it moved (the live cert did its job)
A Track-B live-cert attempt revealed the run-level pin lived at the WRONG layer. The published revision
propagates **per-output** data: `context_source` rides the frozen `approved_llm_outputs.json` (a
DIRECT_ARTIFACT, frozen VERBATIM via `read_bytes()` into the immutable revision). A **top-level** key is
NOT carried by the derived/reader view and never reached Scout's published audit. Rather than add a
publication path just so Scout could see it, we moved the pin to where the published data naturally flows —
onto the output it describes, the same channel `context_source` already uses. Architectural correction,
not a certification workaround.

## The shape to consume (per output, in the frozen approved_llm_outputs.json)
```jsonc
{
  "artifact_id": "1::NEW::1",
  "context_source": [
    {"kind": "supporting_material", "material_id": "mat_...", "category": "character",
     "subtype": "reference", "edition_id": null, "files": [{"file_id": "...", "revision": "rev_..."}]}
  ],
  "grounding_provenance": {                    // NEW — present ONLY when a supporting_material grounded THIS output
    "materials_grounding_version": "v1",
    "resolution_contract_version": "v1"        // pointer to registry/resolution_contract.json, not a copy
  }
}
```
- **Present ONLY when** that output has a `kind == "supporting_material"` contribution in its
  `context_source`. Off / registry-only → the key is ABSENT and the output is byte-identical to baseline.
- Per-output, so a partial recall keeps each panel's own provenance on its own output (no run-level
  carry-forward, none needed).
- Still pins to `resolution_contract_version` (v1) — mark a methodology boundary if it changes; treat a
  version bump on either field as a methodology change.

## Backward compatibility (important for your abstain logic)
- **Existing published revisions frozen before this change are immutable** — they carry whatever they had
  (a run-level `materials_grounding`, or nothing). Do NOT expect per-output `grounding_provenance` on
  those. Handle its ABSENCE gracefully (same as a missing `context_source`) — this is the off→on class you
  already handle from Round 1.
- Only NEW grounded generations under CBI-2c stamp the per-output field.

## Status
- **Engineering-certified:** Gate A (founder-approved) + Gate B (hostile-reviewer PASS). Commit `79823b8`
  on `week12-day2-knowledge-migration`. Publication + provenance modules unchanged; version-pointer only.
- **Track B live-cert (a grounded generate-then-approve revision on #1) is still pending the founder's go**
  (production LLM cost + a new edition). I'll ping this bridge with the revision id the moment it exists —
  at which point you'll have a real frozen `approved_llm_outputs.json` carrying per-output
  `grounding_provenance` to cert Track B against.

## Track A unaffected
`resolved_materials.json` (your Track A diff target) is unchanged by this correction — it already pins
`resolution_contract_version` and is references-only. No action there.

Net: re-point Track B from top-level `materials_grounding` to per-output `output.grounding_provenance`;
handle its absence on pre-CBI-2c revisions; the live grounded revision follows. — Johnny
