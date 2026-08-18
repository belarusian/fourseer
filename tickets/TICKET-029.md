# TICKET-029: Add frozen `CycleClassification` value object to `fourseer/models.py`

## Title
Add a frozen `CycleClassification` dataclass to `fourseer/models.py` that holds
the failure-mode class for one executed cycle.

## Evidence
`fourseer/models.py` defines the per-cycle value objects `CycleMetrics` and the
run-level `RunSummary`, but has NO failure-mode classification object.
`grep -rn "CycleClassification" fourseer/ tests/` returns no matches. The
`__init__.py` docstring references a `fourseer.taxonomy` submodule that does not
exist yet.

The Cycle 7 briefing specifies the fields:
- `cycle_no: int`
- `mode: str` — a stable machine tag from a small CLOSED set:
  `"wall_clock_kill"`, `"max_steps"`, `"task_complete"`, `"execution_error"`,
  `"format_error"`, `"other"`.
- `gate: str | None` — `"green"` / `"red"` / `None` (no Results row).
- `merged: bool | None` — `True` / `False` / `None` (unknown).

## Impact
Without `CycleClassification` there is no place to hold the per-cycle
failure-mode class that `classify_cycle` (TICKET-031) and `classify_run`
(TICKET-032) must return. The Taxonomy phase (cycles 7-8) cannot begin.

## Suggestion
In `fourseer/models.py`, add a `@dataclass(frozen=True) class
CycleClassification` with the four fields above, each with a per-field
docstring (matching the existing style of `CycleMetrics` / `RunSummary`).
Document the closed `mode` set in the class docstring. Pure value object: no
I/O, no side effects, stdlib-only. Add `CycleClassification` to the module
docstring's model list.
