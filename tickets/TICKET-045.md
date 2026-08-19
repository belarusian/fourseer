# TICKET-045: `planned_cycle_set` in drift.py

## Title
Add `planned_cycle_set(gate_log: GateLog) -> set[int]` to `fourseer/drift.py`
that returns the set of cycle numbers the Build Order table plans.

## Evidence
`fourseer/drift.py` has issue-drift functions but no plan-drift helpers. The
Build Order table's `Cycles` column (each `BuildOrderRow.cycles`, e.g. `"1-3"`,
`"7"`) is the "planned" source; plan drift needs the union of every row's range
as a `set[int]`.

## Impact
Without it, `detect_plan_drift` cannot compute the planned set, so the
planned-vs-executed diff cannot be taken.

## Suggestion
In `fourseer/drift.py`, add `planned_cycle_set(gate_log) -> set[int]`: parse each
`BuildOrderRow.cycles` range (`"1-3"` -> `{1,2,3}`, `"7"` -> `{7}`) and return
the union. Tolerate a single number, a range, and unparseable/empty strings
(contribute nothing). Return `set()` when there is no Build Order. Pure,
deterministic, stdlib-only, no I/O, no mutation.
