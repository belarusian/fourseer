# TICKET-033: Re-export taxonomy symbols + focused tests (incl. one real-seed test)

## Title
Re-export `CycleClassification`, `classify_cycle`, `classify_run` from
`fourseer/__init__.py` and add focused unit tests (inline fixtures) plus exactly
one real-seed test.

## Evidence
`fourseer/__init__.py` `__all__` has no taxonomy symbols. The briefing requires
re-exports (model under `# models`, functions under a new `# taxonomy` group)
and tests: focused unit tests using small INLINE fixtures (hand-built
`CycleMetrics` / `Run` / `GateLog` objects, NOT the full seed) for every new
function, plus exactly ONE real-seed test (using the `seed_dir` fixture) that
runs `classify_run(load_run(seed_dir))` and asserts a small, stable, documented
slice.

## Impact
Without re-exports the taxonomy is not part of the public API. Without tests the
closed `mode` set, the `gate`/`merged` enrichment, the kill handling, and the
seed's inconsistency robustness are unpinned.

## Suggestion
In `fourseer/__init__.py`, import and add to `__all__`: `CycleClassification`
(under `# models`), `classify_cycle` and `classify_run` (under a new
`# taxonomy` group). Update the docstring submodule list. Add
`tests/test_taxonomy.py` with focused inline-fixture unit tests (each `mode`
tag, `gate`/`merged` populated vs `None`, no-mutation/determinism, sorted
`classify_run`, seed-inconsistency robustness) + exactly ONE real-seed test
asserting: a `task_complete` cycle's `mode`, a `max_steps` cycle's `mode`, each
of the three kills (21/22/25) -> `"wall_clock_kill"`, and that `gate`/`merged`
are populated for a cycle with a Results table and `None` for a kill.
