# TICKET-038: Focused tests for taxonomy summary (incl. one real-seed test)

## Title
Add focused unit tests (inline fixtures) for `summarize_taxonomy` /
`render_taxonomy` plus exactly one real-seed test.

## Evidence
`tests/test_taxonomy.py` covers cycle-7 `classify_cycle` / `classify_run` but
has no tests for the cycle-8 summary. `grep -n "summarize_taxonomy\|
render_taxonomy\|TaxonomySummary" tests/` returns no matches.

## Impact
Without tests the distribution invariants (mode partition, gate/merge
partition, unknown counts), the renderer's stable ordering, and the seed's
gate-log / `cycles.out` asymmetry robustness are unpinned.

## Suggestion
In `tests/test_taxonomy.py`, add focused inline-fixture unit tests (hand-built
`CycleClassification` lists, NOT the full seed): empty list, single mode,
multiple modes, gate green/red/None partition, merged True/False/None
partition, invariants (`sum(mode_counts.values()) == cycle_count`,
`gate_counts + gate_unknown == cycle_count`, etc.), determinism + no-mutation,
and `render_taxonomy` (header, present-mode ordering, absent-mode omission,
zero-count omission, None/absent rendering). Add exactly ONE real-seed test
(using the `seed_dir` fixture) that computes
`summarize_taxonomy(classify_run(load_run(seed_dir)))` and asserts a small,
stable, documented slice: `cycle_count == 22`,
`mode_counts == {"task_complete": 12, "max_steps": 7, "wall_clock_kill": 3}`,
`gate_unknown == 2`, `merged_unknown == 2`, and that `gate_counts` /
`merged_counts` sum correctly.
