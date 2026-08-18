# TICKET-014: Add frozen `CycleMetrics` value object to `fourseer/models.py`

## Title
Add a frozen `CycleMetrics` dataclass to the models module: a pure value object
holding the per-cycle metrics produced by the Report phase's join/aggregation.

## Evidence
`fourseer/models.py` currently defines `Trajectory`, `CycleRecord`,
`BuildOrderRow`, `CycleBlock`, `GateLog`, `CommitRecord`, `Run`, and
`ConsistencyIssue`. There is no type to represent the *joined, aggregated*
per-cycle record that the Report phase (cycles 4-6) must produce: a cycle's
outcome, its step count (from the joined trajectory), its wall-clock duration,
and the name of the joined trajectory. The aggregation function (TICKET-015)
needs a stable, hashable, comparable value object it can return in a
deterministic list.

## Impact
Without a dedicated type, `build_cycle_metrics` would have to return ad-hoc
dicts or tuples, losing self-documentation, type safety (mypy), and a stable
sort key. The Report renderer (cycle 5) and the Taxonomy/Drift phases will
consume these metrics, so a first-class model is required now.

## Suggestion
In `fourseer/models.py`, add:

```python
@dataclass(frozen=True)
class CycleMetrics:
    cycle_no: int
    outcome: str | None          # CycleRecord.outcome; None for wall-clock kills
    step_count: int              # joined trajectory's step_count; 0 when none joined
    duration_seconds: int | None # wall-clock seconds; None when not computable
    trajectory_name: str | None  # joined Trajectory.name; None when none joined
```

- `outcome` is `None` for a wall-clock-killed cycle (no `OUTER outcome:` line).
- `step_count` is `0` when no trajectory is joined (kills have no trajectory).
- `duration_seconds` is `None` when the cycle has no following start (the last
  cycle in file order) — see TICKET-015 for the duration semantics.
- `trajectory_name` is the joined `Trajectory.name` (basename) or `None`.
- Frozen (immutable) so instances are hashable and safe to sort/dedupe.

## Tests
`tests/test_models.py`: construct a `CycleMetrics`, assert field values, assert
frozen-ness (mutation raises `FrozenInstanceError`), and that two identical
instances compare equal and hash equal.
