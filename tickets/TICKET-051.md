# TICKET-051: `fourseer taxonomy` subcommand wiring

## Title
Wire the `taxonomy` subcommand in `fourseer/cli.py` to
`load_run` → `classify_run` → `summarize_taxonomy` → `render_taxonomy`.

## Evidence
The library pieces exist and are re-exported from the package root
(`fourseer/__init__.py`):
- `fourseer/load.py:43` `load_run(ai_dir, repo_path) -> Run`
- `fourseer/taxonomy.py` `classify_run(run) -> list[CycleClassification]`
- `fourseer/taxonomy.py` `summarize_taxonomy(classifications) -> TaxonomySummary`
- `fourseer/taxonomy.py` `render_taxonomy(summary) -> str`
But there is no `cli.py` (see TICKET-049) and no subcommand that composes them.
The README promises "taxonomy — failure-mode classes: wall-clock-kill,
max_steps, red-gate, incomplete-vs-merged" with no command.

## Impact
The documented `taxonomy` capability has no CLI surface. A user cannot run
`fourseer taxonomy <ai-dir>` to get the run-level failure-mode distribution
(modes / gates / merged).

## Suggestion
In `fourseer/cli.py`, add a `taxonomy` subparser that:
- accepts the AI-artifact directory (positional `ai_dir`) and optional `--repo`;
- on invocation: `run = load_run(ai_dir, repo)`;
  `classifications = classify_run(run)`;
  `summary = summarize_taxonomy(classifications)`;
- prints `render_taxonomy(summary)` to stdout (ends with a trailing newline)
  and returns `0`.
Add `tests/test_cli.py::test_taxonomy_*` covering: a hand-built inline `Run`
whose outcomes span at least two modes (e.g. one `max_steps_reached`, one
`exit:task_complete`, one `None` kill) asserting the header
`# Failure-Mode Taxonomy (N cycles)` and the `modes:` line; and exactly ONE
real-seed test (gated on `seed_dir`) asserting the documented mode distribution
for the seed (22 cycles; wall_clock_kill=3, max_steps_reached=5,
task_complete=14 — pin the exact counts by running `classify_run` against the
seed and recording them).
