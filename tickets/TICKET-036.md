# TICKET-036: Add `render_taxonomy` to `fourseer/taxonomy.py`

## Title
Add `render_taxonomy(summary: TaxonomySummary) -> str` to `fourseer/taxonomy.py`.

## Evidence
`fourseer/taxonomy.py` has no renderer. `grep -n "render_taxonomy"
fourseer/taxonomy.py` returns no matches. The briefing requires a short,
deterministic human-readable block consistent in style with `render_summary` /
`render_report`.

## Impact
Without `render_taxonomy` the run-level distribution cannot be rendered for a
human / CLI consumer.

## Suggestion
In `fourseer/taxonomy.py`, add `render_taxonomy(summary) -> str`. Pure,
deterministic, stdlib-only, no I/O, no mutation. A header line (e.g.
`# Failure-Mode Distribution (N cycles)`), one line per mode tag that is present
(in a stable, documented order), and the gate / merge distribution lines. An
absent mode is simply not listed; a zero count is not listed. `None` / absent
values render deterministically. Add to `__all__`.
