# TICKET-046: `detect_plan_drift` in drift.py

## Title
Add `detect_plan_drift(gate_log: GateLog, executed: set[int]) -> list[PlanDrift]`
to `fourseer/drift.py` that returns the structured diff between the planned set
and the executed set.

## Evidence
`fourseer/drift.py` has `detect_issue_drift` but no plan-drift detector. Plan
drift is the symmetric difference between the planned set (from
`planned_cycle_set`) and the caller-supplied executed set (the
`CycleRecord.cycle_no` values from `cycles.out`), tagged by direction.

## Impact
Without it, the planned-vs-executed mismatch cannot be surfaced as structured,
testable rows.

## Suggestion
In `fourseer/drift.py`, add `detect_plan_drift(gate_log, executed) ->
list[PlanDrift]`: one `PlanDrift` per cycle that is `executed_not_planned` (in
`executed` but not planned) and/or `planned_not_executed` (planned but not in
`executed`). A cycle in BOTH sets is in-plan and produces no row (default: emit
only the drifted rows — document the choice). Return `[]` when planned ==
executed. Sorted by `cycle_no` (stable), deduped (one row per cycle). Robust to
an empty Build Order (every executed cycle is `executed_not_planned`) and an
empty executed set (every planned cycle is `planned_not_executed`). Pure,
deterministic, stdlib-only, no I/O, no mutation.
