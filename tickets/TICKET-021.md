# TICKET-021: Re-export `render_report` and `extract_tokens_cost` from the package root

## Title
Extend `fourseer/__init__.py` to re-export the two new report functions and add
them to `__all__`.

## Evidence
`fourseer/__init__.py` currently re-exports `build_cycle_metrics` under a
`# report` group in `__all__`. The two new functions from TICKET-019 and
TICKET-020 (`render_report`, `extract_tokens_cost`) live in `fourseer/report.py`
but are not importable from the package root, so consumers (and the future CLI,
cycle 11-12) cannot use them without reaching into the submodule.

## Impact
The public API would be inconsistent: `build_cycle_metrics` is top-level but the
renderer and extractor are not. The smoke test (`tests/test_smoke.py`) asserts
the report functions are importable from the root and present in `__all__`, so
it must be extended too.

## Suggestion
In `fourseer/__init__.py`:
- `from fourseer.report import build_cycle_metrics, extract_tokens_cost, render_report`
- Add `"render_report"` and `"extract_tokens_cost"` to `__all__` under the
  `# report` group.
- Update the module docstring's submodule list for `fourseer.report` to mention
  the renderer + token/cost extractor.
- `tests/test_smoke.py`: assert both new names are importable from the root and
  in `__all__`.

Note: `extract_tokens_cost` returns a plain `tuple[int | None, float | None]`
(the primary form from TICKET-020), so NO new `TokenCost` model is added in this
cycle (keeps the change minimal; a value object can be introduced later if the
report needs it as a first-class column).
