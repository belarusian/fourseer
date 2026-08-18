# TICKET-018: Exactly ONE real-seed test for `build_cycle_metrics`

## Title
Add exactly ONE real-seed test (using the `seed_dir` fixture) that runs
`build_cycle_metrics(load_run(seed_dir))` and asserts a small, stable,
documented slice of the result.

## Evidence
The seed is the first real dataset fourseer analyzes. A single seed-backed test
pins the aggregator's behavior on the actual dataset. The seed's `cycles.out`
records 22 cycles (7-28), with wall-clock kills at 21/22/25 (no `OUTER` lines)
and a midnight wrap between cycle 19 (`23:23:29Z`) and cycle 20 (`00:17:48Z`).
Derived values (computed against the seed during this cycle):

- `len(metrics) == 22`
- cycle 7: `step_count == 82`, `duration_seconds == 3505`,
  `trajectory_name == "trajectory_0013.json"`
- cycle 19: `duration_seconds == 3259` (midnight wrap: `00:17:48 - 23:23:29`
  is negative, so `+ 86400`)
- cycles 21, 22, 25 (kills): `step_count == 0`, `duration_seconds == 3600`,
  `trajectory_name is None`
- cycle 28 (last in file order): `duration_seconds is None`,
  `step_count == 39`, `trajectory_name == "trajectory_0043.json"`

## Impact
Without a seed test the aggregator is only verified on synthetic inputs; the
real dataset (kills, midnight wrap, the final `None` duration) would be
unpinned. The test must SKIP when the seed is absent (via the `seed_dir`
fixture) so CI stays green on machines without the local seed.

## Suggestion
`tests/test_report.py`: one `def test_build_cycle_metrics_seed(seed_dir)` that
loads the seed, builds the metrics, and asserts the documented slice above
(number of metrics, a specific joined cycle's step/duration/name, the midnight-
wrap cycle's duration, the kills' zero-step/3600s/None-name, and the last
cycle's `None` duration).

## Tests
The ticket IS the test plan; implement the single seed test in
`tests/test_report.py`.
