# TICKET-019: Implement `render_report` — deterministic human-readable report renderer

## Title
Add `render_report(metrics: list[CycleMetrics]) -> str` to `fourseer/report.py`.

## Evidence
`fourseer/report.py` (lines 1–107) contains only `build_cycle_metrics` and the
private helper `_timestamp_to_seconds`. There is no function that turns the
`list[CycleMetrics]` it produces into a human-readable string. The README
promises "per-cycle metrics: duration, outcome class, steps, tokens/cost" but
no renderer exists to display them.

The `CycleMetrics` dataclass (models.py) carries exactly five fields:
`cycle_no`, `outcome`, `step_count`, `duration_seconds`, `trajectory_name`. A
renderer over this list is a pure, deterministic, stdlib-only string
transformation.

## Impact
Without `render_report` the fourseer CLI (and any consumer) cannot produce a
human-readable summary of a run's cycles. The library is stuck at "data
structures in, data structures out" with no presentation layer.

## Suggestion
In `fourseer/report.py`, add:

```python
def render_report(metrics: list[CycleMetrics]) -> str:
    """Render per-cycle metrics as a deterministic markdown table.

    - Header line: ``# Per-Cycle Metrics (N cycles)`` where N is ``len(metrics)``.
    - One row per metric, in the GIVEN order (the caller passes the already-
      sorted ``build_cycle_metrics`` output); the renderer must NOT re-sort.
    - Columns: Cycle | Outcome | Steps | Duration (s) | Trajectory.
    - ``None`` values render as a single stable placeholder ``-`` so the table
      stays aligned and stable for kills (outcome/trajectory None) and the last
      cycle (duration None). ``step_count`` and ``cycle_no`` are always ints.
    - Pure: no I/O, no mutation of ``metrics``.
    """
```

Semantics to pin in tests:
- `render_report([])` -> header `(0 cycles)` + table header/separator, no rows.
- A kill row renders `outcome` and `trajectory_name` as `-`; the last cycle
  renders `duration_seconds` as `-`.
- Rows preserve the input order (no re-sort).
- Deterministic: same list -> same string; input not mutated.
