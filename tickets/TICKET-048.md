# TICKET-048: plan-drift re-exports + tests

## Title
Re-export the plan-drift symbols from the package root and add focused unit
tests plus exactly one real-seed test.

## Evidence
`fourseer/__init__.py` re-exports the issue-drift symbols but not the new
plan-drift symbols. The new `PlanDrift` model and the three `fourseer/drift.py`
functions (`planned_cycle_set`, `detect_plan_drift`, `render_plan_drift`) need
to be part of the public API and covered by tests.

## Impact
Without re-exports the symbols are not importable from the package root; without
tests the new behavior is unverified.

## Suggestion
In `fourseer/__init__.py`, re-export `PlanDrift` (under `# models`) and
`planned_cycle_set` / `detect_plan_drift` / `render_plan_drift` (under the
existing `# drift` group); add all four to `__all__`. In `tests/test_drift.py`,
add focused inline-fixture unit tests (hand-built `GateLog` / `BuildOrderRow` /
`set[int]` executed sets, NOT the full seed) for each function (range parsing,
single-number, empty Build Order, empty executed set, symmetric difference,
in-plan no-row, sorted/deduped, determinism, no-mutation; render empty/single/
multiple/header/trailing-newline/determinism/no-mutation; `PlanDrift` fields/
frozen/hashable/`code` default; package-root re-exports). Add exactly ONE
real-seed test (gated on the `seed_dir` fixture) that runs
`detect_plan_drift(load_run(seed_dir).gate_log, {c.cycle_no for c in
load_run(seed_dir).cycles})` and pins the documented slice: planned `{1..20}`,
executed `{7..28}`, `executed_not_planned` `{21..28}`, `planned_not_executed`
`{1..6}`.
