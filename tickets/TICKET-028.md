# TICKET-028: Tests for Cycle 6 (inline fixtures + ONE real-seed test)

## Title
Add focused unit tests for `summarize_run` (and `render_summary` if added)
using small INLINE fixtures, plus exactly ONE real-seed test pinning a stable,
documented slice of `summarize_run(build_cycle_metrics(load_run(seed_dir)),
load_run(seed_dir).trajectories)`.

## Evidence
`tests/test_report.py` covers `build_cycle_metrics`, `render_report`, and
`extract_tokens_cost` (each with inline fixtures and one `seed_dir` test). There
are NO tests for `summarize_run` / `render_summary` (they do not exist yet —
TICKET-025/026). The `seed_dir` fixture (tests/conftest.py) skips when the seed
is absent.

The real-seed slice is DERIVED (computed against the seed, not guessed):
`summarize_run(build_cycle_metrics(load_run(seed_dir)),
load_run(seed_dir).trajectories)` yields:
- `cycle_count == 22`
- `completed_count == 19`
- `killed_count == 3`
- `total_steps == 1002`
- `total_duration_seconds == 51106`
- `cycles_with_duration == 21`
- `total_tokens is None` and `total_cost is None` (the seed carries no usage
  records; see `extract_tokens_cost`'s conservative line-anchored match).

## Impact
Without tests, the run-level aggregation (especially the join semantics in
TICKET-025: join over the SET of referenced trajectory names, not all 44
trajectories, and not per-cycle) is unverified and the seed contract is not
pinned. The cycle gate (pytest + ruff + mypy) cannot confirm the feature.

## Suggestion
In `tests/test_report.py`, add:
- Inline-fixture tests for `summarize_run`: empty metrics; all-completed;
  all-killed; mixed; durations present/absent (last cycle None);
  `trajectories=None` -> tokens/cost None; a joined trajectory WITH usage ->
  tokens/cost summed; a trajectory referenced by two cycles counted ONCE; an
  unreferenced trajectory in the list NOT counted; determinism + no mutation.
- If `render_summary` is added: header count, `-` placeholder for None
  tokens/cost, determinism, no mutation.
- Exactly ONE `test_real_seed_summary(seed_dir)` asserting the derived slice
  above (22 / 19 / 3 / 1002 / 51106 / 21, and tokens/cost None).
