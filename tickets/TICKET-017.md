# TICKET-017: Focused inline-fixture unit tests for `build_cycle_metrics`

## Title
Add `tests/test_report.py` with focused unit tests for `build_cycle_metrics`
using small hand-built `Run` objects (NOT the full seed), covering the join,
the duration computation, and the purity/determinism guarantees.

## Evidence
The Report phase's core function must be proven correct on controlled inputs
before it is trusted on the seed. The behaviors that need pinning are: (1) the
trajectory join by basename, (2) the no-join path for a wall-clock kill
(`step_count == 0`, `trajectory_name is None`), (3) duration as
start-to-next-start, (4) the midnight wrap (a negative raw diff becomes
positive after adding 86400), (5) the last cycle's `duration_seconds is None`,
(6) output sorted by `cycle_no`, and (7) no mutation of the input `Run` plus
determinism (same `Run` -> equal list).

## Impact
Without these tests the duration semantics (especially the midnight wrap and
the last-cycle `None`) and the join key are unverified; a regression in the
aggregation would only surface on the seed, which is local-only and skipped in
CI.

## Suggestion
`tests/test_report.py` with small inline fixtures (hand-built `Run` objects
with 2-4 `CycleRecord`s and a few `Trajectory`s):
- join by basename (a cycle whose `trajectory_path` basename matches a loaded
  `Trajectory.name` gets its `step_count` and `trajectory_name`).
- no-join for a kill (`trajectory_path is None` -> `step_count == 0`,
  `trajectory_name is None`).
- duration start-to-next-start (two cycles, known timestamps).
- midnight wrap (e.g. `23:23:29Z` -> `00:17:48Z` yields a positive duration).
- last cycle `duration_seconds is None`.
- output sorted by `cycle_no` (feed records out of order).
- no-mutation + determinism (call twice, assert equal and that the input
  `Run` is unchanged).

## Tests
The ticket IS the test plan; implement the listed cases in `tests/test_report.py`.
