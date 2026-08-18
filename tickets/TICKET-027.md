# TICKET-027: Re-export `RunSummary` / `summarize_run` / `render_summary` in `__init__.py`

## Title
Extend `fourseer/__init__.py` to re-export the new Cycle 6 public surface
(`RunSummary`, `summarize_run`, and `render_summary` if added) and add them to
`__all__`.

## Evidence
`fourseer/__init__.py` (66 lines) re-exports the public API. Its `__all__`
(ends at line 66) currently lists, under `# report`:
`build_cycle_metrics`, `render_report`, `extract_tokens_cost` — and under
`# models`: `CycleMetrics` and the other dataclasses. `RunSummary`,
`summarize_run`, and `render_summary` are absent. The module docstring
(lines 1–16) describes `fourseer.report` as "per-cycle metrics + report
renderer + tokens/cost" and does not mention run-level summary.

## Impact
Even after `RunSummary` / `summarize_run` / `render_summary` are implemented
(TICKET-024/025/026), they are not part of the package's public surface. A
consumer doing `from fourseer import summarize_run` would fail, and the
`__all__` contract (used by `from fourseer import *` and by API docs) would be
incomplete.

## Suggestion
In `fourseer/__init__.py`:
- `from fourseer.models import RunSummary` (add to the existing models import).
- `from fourseer.report import summarize_run, render_summary` (extend the
  existing report import).
- Add `"RunSummary"` to the `# models` group and `"summarize_run"` /
  `"render_summary"` to the `# report` group in `__all__`.
- Update the module docstring's `fourseer.report` line to mention the run-level
  summary.
