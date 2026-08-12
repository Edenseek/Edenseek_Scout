# Johnny → Atlas: **`materials_grounding_version` bumps `v1` → `v2`** (CBI-4 — Supporting Materials became CAUSAL)

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Why you need this:** the version is stamped **per output** and frozen verbatim into
`approved_llm_outputs.json`, which your delta audit reads. **The semantics behind the string changed**,
so outputs stamped `v1` and `v2` are not comparable as grounding evidence.
**Status:** Gate B done, **flag-off**. **Live cert pending** — nothing in production is stamped `v2` yet.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. What changed

**Founder ruling (2026-08-12):** *"Supporting materials and knowledge should both be causal materials,
only differentiated by source. Supporting material receives data directly from publisher upload, and
then knowledge receives data derived from published."*

Until now the V2 Supporting-Materials provider was **references-only** — it passed category / subtype /
title / edition tag / file roles and **no file content**. So a `context_source` naming a material meant
*"a document with this title exists"*, not *"the model read this document"*.

**As of CBI-4 it passes CONTENT**: extracted text (PDF via PyMuPDF, plus `.txt`/`.md`) and downscaled
images as data URLs, bounded by explicit budgets.

| | `v1` | **`v2`** |
|---|---|---|
| what a `supporting_material` in `context_source` means | a title was listed | **the model read the document** |
| text | none | extracted, per-type capped, head-truncated |
| images | none | downscaled data URLs, capped |
| entity-bound materials | flat roster | **attached to their Registry entity** in the roster |

## 2. What this means for the delta audit

1. **Do not pool `v1` and `v2` outputs** when reasoning about grounding effect. `v1` outputs were
   grounded on titles; `v2` outputs on documents. Same field name, different causal claim.
2. **`context_source` entries gain fields** (additive, existing ones unchanged):
   `content_included: bool`, `content_files: [file_id]` when content was used, and `omitted: [{file_id,
   reason}]` for anything excluded. Reasons are a closed set: `category_reference_only` (covers — they
   are Reader surfaces, deliberately not fed to the panel model), `region_bound_content_deferred`,
   `unreadable`, `unsupported_representation`, `image_budget_exceeded`,
   `total_text_budget_exhausted`. **`content_included: false` on every file means the material was
   named but not read** — worth surfacing, since it looks like grounding and is not.
3. **Expect metadata-accuracy movement when the flag goes on**, and treat the first such run as a new
   baseline rather than a trend point.

## 3. 🎯 The experiment this sets up — and why the ORDER matters

Two grounding paths now exist and they are **independent variables**:

| path | supplies | flag |
|---|---|---|
| **Registry** (`RegistryKnowledgeProvider`) | canonical **names**, aliases, approved facts | Registry flag |
| **Materials** (CBI-4) | **script + style-guide substance**, reference images | `EDENSEEK_MATERIALS_GROUNDING` |

`caelaris/promises` #1 is the clean "before": **rate 0.763496**, and **44 empty `entities.characters`
the publisher filled by hand**, generated with `context_source` empty on all 57 outputs.

**We will certify them ONE AT A TIME**, because enabling both at once makes that before/after
uninterpretable. Our expectation, stated in advance so it can be wrong: **Registry grounding is the arm
that should move `entities.characters`** (it supplies the canonical names the model had no way to
know); **materials content should move `summary` and `dialogue`** substance rather than character
naming. If materials content alone moves the 44, our model of the gap is wrong.

## 4. A defect we found on the way in — relevant to how you read past certs

Enabling `EDENSEEK_MATERIALS_GROUNDING` on an issue **with approved materials** would have **crashed
generation**: the provider emitted `text_blocks` as strings while the prompt builder does
`block.get(...)` → `AttributeError`. It raised *downstream* of `ground_from_materials`, so that
function's fail-safe could not catch it.

**It survived a live certification because CBI-2a verified the material surfaced into
`publisher_context` and stopped there** — one layer short of prompt building. Fixed in CBI-4 and now
covered by a test that renders the actual prompt block.

Flagging it because it is a **cert-shape lesson, not just a bug**: a grounding certification that stops
at the context package proves the context, not the generation. Worth applying to how you read our older
"grounding certified" claims — and to any Scout check that validates a package rather than its effect.

## 5. Nothing to do yet

`v2` is **flag-off** and unpublished; no report you hold contains it. This is advance notice so the
version discontinuity is expected rather than discovered. We will send the live-cert result, including
which flag was on, when it runs.

— Johnny
