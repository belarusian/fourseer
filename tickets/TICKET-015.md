# TICKET-015: Add `fourseer/report.py` with `build_cycle_metrics(run)`

## Title
Create a new `fourseer/report.py` module exposing a pure, deterministic,
stdlib-only `build_cycle_metrics(run: Run) -> list[CycleMetrics]` that joins
each `CycleRecord` with its trajectory and computes its wall-clock duration.

## Evidence
The Report phase (cycles 4-6) must turn the four sources into per-cycle
metrics. The join key is the trajectory basename: a `CycleRecord.trajectory_path`
(e.g. `.../trajectory_0013.json`) must be matched against the loaded
`Trajectory.name` set (populated by the loader in cycle 3). A cycle whose
`trajectory_path is None` (a wall-clock kill) joins no trajectory. Duration is
measured start-to-next-start from the `HH:MM:SSZ` timestamps in `cycles.out`
(the append-only stream has no per-cycle end timestamp), with a midnight wrap
(a negative raw diff means the next start crossed midnight, so add 86400). The
last cycle in file order has no following start, so its duration is `None`.

## Impact
Without this function there is no per-cycle metric to report, classify, or
render. The renderer (cycle 5) and the taxonomy (cycles 7-8) both depend on a
stable, sorted list of `CycleMetrics`.

## Suggestion
In `fourseer/report.py`:

```python
def build_cycle_metrics(run: Run) -> list[CycleMetrics]: ...
```

- Build a `{name: Trajectory}` map from `run.trajectories`.
- For each `CycleRecord` (in file order): join its trajectory by
  `PurePosixPath(trajectory_path).name` when `trajectory_path is not None`.
- `step_count` = joined trajectory's `step_count`, else `0`.
- `trajectory_name` = joined trajectory's `name`, else `None`.
- `duration_seconds`: parse this cycle's and the next cycle's timestamps to
  seconds-of-day; `diff = next - cur`; if `diff < 0`, `diff += 86400`. The last
  cycle in file order has `duration_seconds = None`.
- Return the list sorted by `cycle_no`.
- Pure: no I/O, no mutation of `run`, deterministic for the same `Run`.

## Tests
`tests/test_report.py`: focused inline-fixture unit tests (hand-built `Run`
objects with a few records) covering: join by basename, no-join for a kill
(`step_count == 0`, `trajectory_name is None`), duration start-to-next-start,
midnight wrap (a `23:23:29Z` -> `00:17:48Z` pair yields a positive duration),
last-cycle `duration_seconds is None`, sorted-by-`cycle_no` output, and
no-mutation/determinism. Plus exactly ONE real-seed test (see TICKET-018).
