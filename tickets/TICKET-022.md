# TICKET-022: Unit tests for `render_report` and `extract_tokens_cost` (inline fixtures)

## Title
Add focused unit tests for the two new functions using small INLINE fixtures
(hand-built `CycleMetrics` lists and `Trajectory` objects), NOT the full seed.

## Evidence
`tests/test_report.py` currently covers only `build_cycle_metrics`. The two new
functions need their own coverage. Per the cycle constraints, every new function
gets focused unit tests with inline fixtures, plus exactly ONE real-seed test
(see TICKET-023).

## Impact
No coverage means the renderer's placeholder/ordering/determinism semantics and
the extractor's conservatism (no false-positives on incidental prose) are
unpinned.

## Suggestion
In `tests/test_report.py` (or a new `tests/test_report_render.py`), add:

`render_report`:
- empty list -> header `(0 cycles)` + table header/separator, no data rows.
- a kill row (outcome None, trajectory_name None) renders `-` in those columns.
- the last cycle (duration_seconds None) renders `-` in the duration column.
- rows preserve the GIVEN order (pass an unsorted list; assert row order matches
  input, i.e. the renderer does NOT re-sort).
- deterministic + no mutation: same list -> same string; input list unchanged.
- header line is exactly `# Per-Cycle Metrics (N cycles)` for the given N.

`extract_tokens_cost`:
- a trajectory whose message content has a `usage: tokens=123 cost=0.45` line
  -> `(123, 0.45)`.
- a trajectory with `usage: tokens=123` (no cost) -> `(123, None)`.
- a trajectory with incidental prose (a shell `usage()` function +
  `FIVE_MAX_TOKENS=65536`, TS `prompt_tokens: number;`, the word "usage" in a
  comment) -> `(None, None)` (no false-positive).
- multiple usage lines -> tokens and cost summed.
- empty trajectory (no messages) -> `(None, None)`.
- no mutation: the trajectory's messages are unchanged after the call.
