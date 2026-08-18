# TICKET-011: New `fourseer/validate.py` — `validate_run(run) -> list[ConsistencyIssue]`

## Title
Add a pure, deterministic, stdlib-only consistency validator that cross-checks
the four parsed sources in a `Run` and returns a stable, sorted list of
`ConsistencyIssue` objects.

## Evidence
Cycles 1-2 give us the four parsers and the `Run` aggregate, but nothing that
cross-checks the sources against each other. The seed itself is a good example
of why this matters: `cycles.out` records cycles 7-28, the gate log has blocks
1-20 and 23-28, and the Build Order table only plans cycles 1-20 — so cycles
21-28 were executed outside any planned range, and cycles 21/22/25 have no gate
block. A consumer needs a structured, testable way to surface exactly these
disagreements before computing per-cycle metrics.

## Impact
The Report phase (cycles 4-6) should not silently compute metrics over a
run whose artifacts disagree. `validate_run` is the bridge: it lets fourseer
say "these artifacts disagree in these ways" as a deterministic list.

## Suggestion
New module `fourseer/validate.py` with:

```python
def validate_run(run: Run) -> list[ConsistencyIssue]:
    ...
```

Checks (each emits `ConsistencyIssue` with a stable `code`):
- (a) `orphan_trajectory_path` — for each `CycleRecord` with a non-None
  `trajectory_path`, the basename (`trajectory_NNNN.json`) must be present in
  the set of loaded `Trajectory.name` values. (cycle_no = the record's number)
- (b) `cycle_not_in_gate_log` — a `CycleRecord.cycle_no` with no matching
  `CycleBlock.cycle_no` in `run.gate_log.cycles`.
- (b') `gate_cycle_not_in_cycles_out` — a `CycleBlock.cycle_no` with no matching
  `CycleRecord.cycle_no` in `run.cycles`.
- (c) `build_order_range_gap` — an executed `CycleRecord.cycle_no` that falls
  outside every Build Order range (parse `cycles` strings like `"1-3"` / `"7"`).

Requirements:
- Pure: no I/O, no mutation of `run`.
- Deterministic: return issues sorted by a stable key (e.g. `(code, cycle_no or -1, detail)`).
- Return `[]` when the run is internally consistent.
- stdlib only.

## Tests
Covered by TICKET-012 (inline fixtures) and TICKET-013 (one real-seed test).
