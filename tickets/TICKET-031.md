# TICKET-031: Add `classify_cycle(metrics, gate_log=None) -> CycleClassification`

## Title
Add `classify_cycle` to a new `fourseer/taxonomy.py` that derives a cycle's
failure-mode `mode` from its `CycleMetrics.outcome` and enriches `gate` /
`merged` from the gate log.

## Evidence
`fourseer/taxonomy.py` does not exist. `fourseer/report.py` has
`build_cycle_metrics` (produces `CycleMetrics` with an `outcome` field) but no
classification. The briefing defines a TOTAL mapping from outcome string to a
closed `mode` tag:
- `outcome is None` -> `"wall_clock_kill"`
- `max_steps_reached` -> `"max_steps"`
- `exit:task_complete` -> `"task_complete"`
- starts with `execution_error` -> `"execution_error"`
- starts with `repeated_format_error` -> `"format_error"`
- anything else -> `"other"`

`gate` / `merged` are best-effort enrichment from the matching `CycleBlock`
(by `cycle_no`): `gate` = the block's `gate_after` (`"green"`/`"red"`),
`merged` = the block's `merged`; both `None` when no block or no row. They must
NOT affect `mode`.

## Impact
`classify_cycle` is the core of the taxonomy. The mapping must be total and
deterministic; `gate`/`merged` must be pure enrichment that never changes
`mode`.

## Suggestion
In `fourseer/taxonomy.py`, add `classify_cycle(metrics: CycleMetrics,
gate_log: GateLog | None = None) -> CycleClassification`. Pure, deterministic,
stdlib-only, no I/O, no mutation. Derive `mode` from `metrics.outcome` via the
total mapping above. When `gate_log` is supplied, look up the
`CycleBlock` with `cycle_no == metrics.cycle_no`; if found, set `gate` /
`merged` from its fields (else `None`).
