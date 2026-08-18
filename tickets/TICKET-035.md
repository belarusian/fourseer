# TICKET-035: Add `summarize_taxonomy` to `fourseer/taxonomy.py`

## Title
Add `summarize_taxonomy(classifications: list[CycleClassification]) ->
TaxonomySummary` to `fourseer/taxonomy.py`.

## Evidence
`fourseer/taxonomy.py` has `classify_cycle` and `classify_run` (cycle 7) but no
run-level roll-up. `grep -n "summarize_taxonomy" fourseer/taxonomy.py` returns
no matches. The briefing requires a pure, deterministic, stdlib-only function
that rolls the per-cycle classifications up into a `TaxonomySummary` (TICKET-034).

## Impact
Without `summarize_taxonomy` the per-cycle classifications cannot be aggregated
into the run-level distribution the Taxonomy phase promises.

## Suggestion
In `fourseer/taxonomy.py`, add `summarize_taxonomy(classifications) ->
TaxonomySummary`. Pure, deterministic, stdlib-only, no I/O, no mutation.
`cycle_count == len(classifications)`. `mode_counts` counts every
classification's `mode` (only tags that appear are keys). `gate_counts` /
`gate_unknown` partition the `gate` field (`"green"` / `"red"` keys; `None`
counted in `gate_unknown`). `merged_counts` / `merged_unknown` partition the
`merged` field (`"merged"` / `"not_merged"` keys; `None` counted in
`merged_unknown`). Add to `__all__`.
