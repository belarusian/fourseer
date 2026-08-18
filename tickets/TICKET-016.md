# TICKET-016: Re-export `CycleMetrics` and `build_cycle_metrics` from the package root

## Title
Extend `fourseer/__init__.py` to re-export the new Report-phase symbols
(`CycleMetrics`, `build_cycle_metrics`), add them to `__all__`, and update the
module docstring's submodule list.

## Evidence
`fourseer/__init__.py` already re-exports the Foundations-phase public surface
(`Run`, `load_run`, `ConsistencyIssue`, `validate_run`, the parsers, and the
models). The docstring already lists `fourseer.report` as a planned submodule
("per-cycle metrics"), but the symbols are not yet importable from the package
root. Consumers (the cycle-5 renderer, the CLI, and tests) should be able to do
`from fourseer import CycleMetrics, build_cycle_metrics`.

## Impact
Without the re-exports, the new Report-phase API is only reachable via the
submodule path (`fourseer.report.build_cycle_metrics`), which is inconsistent
with how every other public symbol is exposed and breaks the smoke test's
`__all__` contract.

## Suggestion
- Import `CycleMetrics` from `fourseer.models` and `build_cycle_metrics` from
  `fourseer.report`.
- Add both to `__all__` (grouped under a `# report` comment).
- The docstring already lists `fourseer.report`; no change needed there, but
  confirm it is present.

## Tests
`tests/test_smoke.py`: assert `CycleMetrics` and `build_cycle_metrics` are
importable from the package root and present in `__all__`.
