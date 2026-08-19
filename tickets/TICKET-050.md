# TICKET-050: `fourseer report` subcommand wiring

## Title
Wire the `report` subcommand in `fourseer/cli.py` to
`load_run` → `build_cycle_metrics` → `render_report` (+ `summarize_run` /
`render_summary`).

## Evidence
The library pieces exist and are re-exported from the package root
(`fourseer/__init__.py`):
- `fourseer/load.py:43` `load_run(ai_dir, repo_path) -> Run`
- `fourseer/report.py:48` `build_cycle_metrics(run) -> list[CycleMetrics]`
- `fourseer/report.py:135` `render_report(metrics) -> str`
- `fourseer/report.py:223` `summarize_run(metrics, trajectories) -> RunSummary`
- `fourseer/report.py:320` `render_summary(summary) -> str`
But there is no `cli.py` (see TICKET-049) and no subcommand that composes them.
The README's `## Usage` section (README.md, line 12) is empty — it promises
"report — per-cycle metrics: duration, outcome class, steps, tokens/cost" but
gives no command.

## Impact
The documented `report` capability has no CLI surface. A user cannot run
`fourseer report <ai-dir>` to get the per-cycle metrics table and run summary.

## Suggestion
In `fourseer/cli.py`, add a `report` subparser that:
- accepts the AI-artifact directory (positional `ai_dir`) and optional `--repo`;
- on invocation: `run = load_run(ai_dir, repo)`;
  `metrics = build_cycle_metrics(run)`;
  `summary = summarize_run(metrics, run.trajectories)`;
- prints `render_report(metrics)` followed by `render_summary(summary)` to
  stdout (both already end with a trailing newline), and returns `0`.
Add `tests/test_cli.py::test_report_*` covering: a hand-built inline `Run`
(2 joined cycles + 1 kill, mirroring `tests/test_report.py::_sample_run`)
asserting the printed table header `# Per-Cycle Metrics (N cycles)` and the
summary header `# Run Summary (N cycles)`; and exactly ONE real-seed test
(gated on `seed_dir`) asserting the documented slice (22 cycles, 19 completed,
3 killed, 1002 steps, 51106 s, 21 with duration, tokens/cost `-`).
