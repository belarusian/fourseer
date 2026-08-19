# TICKET-047: `render_plan_drift` in drift.py

## Title
Add `render_plan_drift(drift: list[PlanDrift]) -> str` to `fourseer/drift.py`
that renders a plan-drift list as a short, deterministic human-readable block.

## Evidence
`fourseer/drift.py` has `render_issue_drift` but no plan-drift renderer. The
plan-drift rows need a deterministic text block consistent in style with
`render_issue_drift` / `render_summary` / `render_taxonomy`.

## Impact
Without it, the plan-drift diff has no human-readable form for the CLI / reports.

## Suggestion
In `fourseer/drift.py`, add `render_plan_drift(drift) -> str`: a header line
`# Plan Drift (N cycles)` where `N` is `len(drift)`; when non-empty, one line per
drifted cycle (in `cycle_no` order) of the form
`cycle <cycle_no>: <status>`; when empty, a single stable no-drift line
`no plan drift detected`. Always ends with a trailing newline. Pure,
deterministic, stdlib-only, no I/O, no mutation.
