# TICKET-037: Re-export taxonomy-summary symbols from `fourseer/__init__.py`

## Title
Re-export `TaxonomySummary`, `summarize_taxonomy`, `render_taxonomy` from
`fourseer/__init__.py` and add them to `__all__`.

## Evidence
`fourseer/__init__.py` `__all__` has the cycle-7 taxonomy symbols
(`CycleClassification`, `classify_cycle`, `classify_run`) but no
taxonomy-summary symbols. `grep -n "TaxonomySummary\|summarize_taxonomy\|
render_taxonomy" fourseer/__init__.py` returns no matches.

## Impact
Without re-exports the run-level taxonomy summary is not part of the public API.

## Suggestion
In `fourseer/__init__.py`, import and add to `__all__`: `TaxonomySummary`
(under `# models`), `summarize_taxonomy` and `render_taxonomy` (under the
existing `# taxonomy` group). Update the docstring submodule list.
