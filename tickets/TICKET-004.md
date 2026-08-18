# TICKET-004: gate-log parser (FIX: multi-line lessons truncated)

## Title
`fourseer/parse/gate_log.py` — `parse_gate_log(text) -> GateLog`.

## Evidence
The gate log is a single append-only markdown file with two machine-relevant
sections:
1. `## Build Order` — a markdown table `Phase | Cycles | Target`; each data
   row -> `BuildOrderRow`. The seed has 6 rows (Foundations 1-3 ... Hardening
   18-20).
2. `## Cycle N` — one block per executed cycle. Header `## Cycle N: <title>`
   (title may be absent, e.g. `## Cycle 1 — Pending`). Body carries optional
   `**Date:**`, `**HEAD (start):**`, `**HEAD (end):**` fields and an optional
   `### Lessons` numbered list. The seed has 26 cycle blocks (1, 2, 3-20,
   23-28).

**BUG:** the current `_parse_cycle_blocks` only captures the FIRST line of each
numbered lesson. A lesson that wraps across multiple lines (very common — the
seed's cycle-3 lessons are 2-4 lines each) is truncated to its first line.
Verified: seed cycle 3 has 3 lessons but the parser returns `lessons=1` with
only the first line of lesson 1.

## Impact
Lessons are a key qualitative signal for the taxonomy/drift cycles. Truncation
loses the substance of every multi-line lesson, making the parsed GateLog
unfaithful to the source.

## Suggestion
When inside the `### Lessons` section, accumulate a numbered item's text across
consecutive non-blank, non-numbered lines (continuation lines) until the next
numbered item or a non-lesson line. Strip the leading `N.` marker from the first
line; append continuation lines (joined with a space or newline). Keep the
Build Order table parsing as-is (it works: 6 rows verified).

## Tests
`tests/test_parse_gate_log.py`:
- inline fixture with a Build Order table (2 rows) + 2 cycle blocks, one with a
  multi-line lesson (2 numbered items, one wrapping 2 lines) -> assert build
  order rows, cycle fields, and that the wrapped lesson is captured in full.
- a cycle block with no Date/HEAD/Lessons -> all None/empty.
- one test against the real seed: `len(build_order) == 6`,
  `len(cycles) == 26`, cycle 3 has 3 lessons and lesson[0] contains the full
  first sentence (not just "Trust SCAN over the briefing.").
