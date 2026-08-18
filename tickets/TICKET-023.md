# TICKET-023: One real-seed test for `render_report` (stable documented slice)

## Title
Add exactly ONE real-seed test (using the `seed_dir` fixture) that renders
`build_cycle_metrics(load_run(seed_dir))` and asserts a small, stable,
documented slice of the output.

## Evidence
The cycle constraints require exactly one seed-backed test for the renderer.
The seed has 22 cycles. The derived, stable slice (from `build_cycle_metrics`
on the seed) is:

- Header line: `# Per-Cycle Metrics (22 cycles)`
- Cycle 7 row: `| 7 | max_steps_reached | 82 | 3505 | trajectory_0013.json |`
- Cycle 21 (a wall-clock kill) row: `| 21 | - | 0 | 3600 | - |`
  (outcome and trajectory_name render as the `-` placeholder; duration 3600)
- Cycle 28 (the last cycle) row: `| 28 | exit:task_complete | 39 | - | trajectory_0043.json |`
  (duration_seconds renders as the `-` placeholder)

## Impact
Pins the renderer's behavior on the actual dataset: the header count, a normal
row, a kill row (two `-` placeholders), and the last-cycle row (duration `-`).

## Suggestion
In `tests/test_report.py`, add `test_real_seed_report(seed_dir)`:
- `run = load_run(seed_dir)`; `text = render_report(build_cycle_metrics(run))`.
- Assert the header line is present and equals `# Per-Cycle Metrics (22 cycles)`.
- Assert the cycle 7 row string is present verbatim.
- Assert the cycle 21 kill row string is present verbatim (two `-` placeholders).
- Assert the cycle 28 last-cycle row string is present verbatim (duration `-`).
- Assert the number of data rows (lines starting with `| ` after the separator)
  equals 22.
