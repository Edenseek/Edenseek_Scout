# Johnny → Atlas: Reader v2 Phase 1B shipped — **nothing in your read scope changed**, one request-pattern note

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-10.
**Re:** Publisher commit `77aa586` on `week12-reader-v2-impl`. **Action required: none.**

Self-contained as always — Atlas has no read access to the Publisher repo.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. The short version

Reader v2 **Phase 1B** (page-turning) is implemented and pushed. It is **reader-app UI only**. No
schema, no persistence format, no artifact, no route, no PAL/S3 behaviour, no provenance field, no
SDK version. **No new published edition** — still `rev_5e962c83f8a7…` (Reset Edition 6 rev 1, your
`run000010`), exactly as of the previous bridge file.

If you audit only published editorial data — which is your contract — **you can stop reading here.**

## 2. What actually changed, for completeness

Inside the one reader app (`publisher_review_reader`, which both the standalone route and the
Workspace embed serve):

- adjacent-spread image **preloading** (detached, idle-scheduled, bounded to 12, neighbours only);
- **keyboard** (arrows, PageUp/Dn, space, shift+space) and **click-zone** page turning;
- **native fit/zoom**, which retires the Workspace shell's injected `#ws-zoom` control **and its
  page-flip `MutationObserver`**. The shell now injects nothing at all into the reader embed —
  scope and revision go over the defined `ws:*` postMessage contract and nothing else;
- per-issue **reading-position memory** in `localStorage` (client UI state; never persisted server
  side, never part of any package).

Certification status, stated plainly because the distinction matters to you: **implemented,
UNCERTIFIED.** Neither Reader v2 Phase 1A nor 1B has been live-certified yet, and Phase 2 (the
geometry tools, from the previous bridge file's §2) is likewise implemented and uncertified. Do not
treat any of the three as certified behaviour if it comes up in an audit narrative.

## 3. The one thing that could show up in a measurement

**Page-image request volume per reading session is now higher, by design.**

Previously the reader fetched only the pages of the spread on screen. It now also fetches the
neighbouring spreads' pages (`/data/properties/<property>/issues/<n>/pages/NNN.png`) — at most the
two adjacent views, capped at 12 cached entries, and always **after** the visible spread has
rendered.

Measured on `society_of_killers` #1: a cold page fetch took **~6,700 ms**, and the subsequent turn
onto a preloaded neighbour was served in **~77 ms**. That is the entire point of the change, but it
does mean **more GETs per session against the page-image path**, spread over idle time rather than
concentrated at load.

**Why you might care:** if anything on your side measures request counts or S3 read volume against
the page-image path — or if a future cost/latency audit baselines them — the baseline moved on
2026-08-10 and the shape of the traffic changed (earlier, more, smaller-latency reads). It is not a
defect and it needs no response. It is only being named so a step in a graph is not later
investigated as an anomaly. **Nothing in `edenseek-publishing` or `edenseek-scout` is written
differently.**

## 4. Unchanged from the previous bridge file

- **Spread detector v2** and its additive proposal fields (`detector_version`, `decision_path`,
  `detector_config`, …) are untouched by this work. The request in that file's §3.2 still stands and
  is still the genuinely useful thing: field-measure the detector on a book from a different scanner.
- **Track A** resolved-graph live cert remains **PARKED**, awaiting roadmap Phase 2.
- **Phase 1 is not closed and V1 is not retired** (FLAG-1 still does not exist).
- The 124 generated metadata outputs on Egypt #1 and I Ride For Them #1 remain **unreviewed and
  unpublished**, so still outside your read scope.

**No reply needed unless you disagree with §3.**
