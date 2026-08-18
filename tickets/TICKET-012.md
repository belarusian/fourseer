# TICKET-012: Focused unit tests for `validate_run` with inline fixtures

## Title
Add `tests/test_validate.py` with focused unit tests for `validate_run` using
small hand-built `Run` objects (NOT the full seed).

## Evidence
TICKET-011 adds `validate_run`. Per the cycle constraints, every new function
needs focused unit tests using small INLINE fixtures (hand-built `Run` objects
with a few records), not the full seed.

## Impact
Without inline-fixture tests, the validator's per-check behavior (each issue
code, the `[]`-when-consistent case, determinism/ordering, and no-mutation) is
unverified and the seed test alone cannot localize a regression to a specific
check.

## Suggestion
`tests/test_validate.py` — build tiny `Run` objects and assert:
- A fully consistent run returns `[]`.
- (a) a `CycleRecord.trajectory_path` whose basename is not among loaded
  `Trajectory.name` values -> exactly one `orphan_trajectory_path` issue with
  the right `cycle_no`.
- (b) a cycle in `cycles` with no gate block -> `cycle_not_in_gate_log`.
- (b') a gate block with no cycle record -> `gate_cycle_not_in_cycles_out`.
- (c) an executed cycle outside all Build Order ranges -> `build_order_range_gap`.
- Determinism: calling twice on the same `Run` yields the same list; the list
  is sorted by the stable key.
- Purity: the input `Run` is not mutated (compare a snapshot before/after).
- A `trajectory_path` that DOES match a loaded trajectory name emits no orphan
  issue.

## Tests
This ticket IS the tests.
