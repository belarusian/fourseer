# TICKET-026: Add `render_summary(summary) -> str` (optional presentation)

## Title
Add an optional `render_summary(summary: RunSummary) -> str` to
`fourseer/report.py` — a short, deterministic human-readable block for the
run-level totals, consistent in style with `render_report`.

## Evidence
`fourseer/report.py` has `render_report` (line 123) which renders per-cycle
metrics as a markdown table with a `# ... (N cycles)` header and a stable `-`
placeholder for `None` values (see `_PLACEHOLDER`, line 120). There is no
renderer for the run-level `RunSummary` (which does not yet exist — see
TICKET-024). The briefing marks `render_summary` as optional but in scope.

## Impact
Without `render_summary` the run-level totals have no presentation layer, so a
consumer cannot display the aggregate (cycle count, completed/killed, total
steps, total duration, tokens/cost) in a stable, human-readable form.

## Suggestion
In `fourseer/report.py`, add: