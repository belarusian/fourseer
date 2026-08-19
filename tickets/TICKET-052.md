# TICKET-052: `fourseer drift` subcommand wiring (plan + issue drift)

## Title
Wire the `drift` subcommand in `fourseer/cli.py` to
`load_run` → `detect_plan_drift` → `render_plan_drift` AND
`detect_issue_drift` → `render_issue_drift`.

## Evidence
The library pieces exist and are re-exported from the package root
(`fourseer/__init__.py`):
- `fourseer/load.py:43` `load_run(ai_dir, repo_path) -> Run`
- `fourseer/drift.py:232` `detect_plan_drift(gate_log, executed) -> list[PlanDrift]`
- `fourseer/drift.py:273` `render_plan_drift(drift) -> str`
- `fourseer/drift.py:99` `detect_issue_drift(commits, open_issues) -> list[IssueDrift]`
- `fourseer/drift.py` `render_issue_drift(drift) -> str`
But there is no `cli.py` (see TICKET-049) and no subcommand that composes them.

Two inputs are derivable from the run, one is NOT:
- plan drift's `executed` set is derivable: `{c.cycle_no for c in run.cycles}`.
- issue drift's `commits` is `run.commits` (populated only when `--repo` given).
- issue drift's `open_issues: set[int]` is NOT derivable from any artifact the
  loader reads — it is the set of issue numbers still open in the tracker.
  Verified against the seed: `load_run(seed).commits == []` (no `--repo`), so
  `detect_issue_drift` returns `[]` regardless of `open_issues`.

Verified against the real seed (plan drift only): `planned={1..20}`,
`executed={7..28}`, so `detect_plan_drift` yields 14 rows — `planned_not_executed`
for cycles 1-6 and `executed_not_planned` for cycles 21-28.

## Impact
The documented `drift` capability has no CLI surface. A user cannot run
`fourseer drift <ai-dir>` to get plan drift (Build Order vs executed) or issue
drift (closed-in-commits-but-still-open). The `open_issues` input has no
documented source, so the issue-drift half is currently unwireable without a
design decision.

## Suggestion
In `fourseer/cli.py`, add a `drift` subparser that:
- accepts the AI-artifact directory (positional `ai_dir`) and optional `--repo`;
- plan drift: `executed = {c.cycle_no for c in run.cycles}`;
  `plan = detect_plan_drift(run.gate_log, executed)`; print
  `render_plan_drift(plan)`.
- issue drift: `open_issues` must be supplied by the caller. Add an
  `--open-issues` option accepting a comma-separated list of issue numbers
  (e.g. `--open-issues 42,43,44`) defaulting to the empty set; then
  `issue = detect_issue_drift(run.commits, open_issues)`; print
  `render_issue_drift(issue)`. Document in the README that issue drift is empty
  unless `--repo` is given AND `--open-issues` is non-empty.
- Print the plan-drift block first, then the issue-drift block, and return `0`.
Add `tests/test_cli.py::test_drift_*` covering: a hand-built inline `Run` with a
Build Order planning cycles 1-3 and executed cycles 2-4 (asserting
`planned_not_executed` for 1 and `executed_not_planned` for 4, and the
`# Plan Drift (N cycles)` / `# Issue Drift` headers); an `--open-issues` parse
test (comma list → `set[int]`, empty default → `set()`); and exactly ONE
real-seed test (gated on `seed_dir`) pinning the verified plan-drift slice
(14 rows: 1-6 planned_not_executed, 21-28 executed_not_planned) with issue
drift empty (no `--repo`).
