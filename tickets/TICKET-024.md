# TICKET-024: Add frozen `RunSummary` value object to `fourseer/models.py`

## Title
Add a frozen `RunSummary` dataclass to `fourseer/models.py` that aggregates a
whole run's per-cycle `CycleMetrics` into a single run-level totals object.

## Evidence
`fourseer/models.py` (309 lines) defines the per-cycle value object
`CycleMetrics` (line 277) but has NO run-level aggregate. The module docstring
(lines 1–24) lists the models it contains (`Trajectory`, `CycleRecord`,
`BuildOrderRow`, `CycleBlock`, `GateLog`, `CommitRecord`, `ConsistencyIssue`,
`CycleMetrics`) — `RunSummary` is absent from both the code and the docstring.
`grep -rn "RunSummary" fourseer/ tests/` returns no matches.

The Cycle 6 briefing specifies the fields:
- `cycle_count: int` (total cycles)
- `completed_count: int` (cycles with a non-`None` outcome)
- `killed_count: int` (cycles with `outcome is None`)
- `total_steps: int` (sum of `step_count`)
- `total_duration_seconds: int` (sum of non-`None` `duration_seconds`; `0` when none)
- `cycles_with_duration: int` (count of non-`None` durations)
- `total_tokens: int | None` (optional)
- `total_cost: float | None` (optional)

## Impact
Without `RunSummary` there is no place to hold the run-level totals that
`summarize_run` (TICKET-025) must return. The Report phase (cycles 4–6) is
incomplete: per-cycle metrics exist but cannot be rolled up into a single
aggregate a consumer (CLI, taxonomy, drift) can hold.

## Suggestion
In `fourseer/models.py`, add a `@dataclass(frozen=True) class RunSummary` with
the eight fields above, each with a per-field docstring (matching the existing
style of `CycleMetrics` / `Run`). Pin the invariant
`completed_count + killed_count == cycle_count` in the docstring. Add
`RunSummary` to the module docstring's model list (lines 1–24). Pure value
object: no I/O, no side effects, stdlib-only.
