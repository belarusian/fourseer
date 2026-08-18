# TICKET-032: Add `classify_run(run) -> list[CycleClassification]`

## Title
Add `classify_run` to `fourseer/taxonomy.py` that classifies every executed
cycle in a `Run`, sorted by `cycle_no`.

## Evidence
`fourseer/taxonomy.py` does not exist. The briefing requires a run-level entry
point that builds `build_cycle_metrics(run)` and classifies each cycle (passing
`run.gate_log`), returning the list sorted by `cycle_no`.

The taxonomy must be robust to the seed's inconsistency: cycles 21/22 are in
`cycles.out` but NOT the gate log (no `CycleBlock`), and cycles 1-6 are in the
gate log but NOT `cycles.out`. So `classify_run` must classify ONLY the cycles
present in `cycles.out` (the `build_cycle_metrics` output) and tolerate a
missing gate-log block (leaving `gate`/`merged` `None`).

## Impact
`classify_run` is the public run-level API the CLI (cycles 11-12) and the
distribution summary (cycle 8) will consume. Classifying the wrong set of cycles
(e.g. the gate-log-only cycles 1-6) would be incorrect.

## Suggestion
In `fourseer/taxonomy.py`, add `classify_run(run: Run) ->
list[CycleClassification]`. Pure, deterministic, stdlib-only, no I/O, no
mutation. Build `build_cycle_metrics(run)`, call `classify_cycle(m,
run.gate_log)` for each, and return the list sorted by `cycle_no`.
