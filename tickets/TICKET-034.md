# TICKET-034: Add frozen `TaxonomySummary` value object to `fourseer/models.py`

## Title
Add a frozen `TaxonomySummary` dataclass to `fourseer/models.py` that aggregates
a whole run's per-cycle failure-mode classifications into a single distribution
summary.

## Evidence
`fourseer/models.py` defines the per-cycle `CycleClassification` (cycle 7) but
has NO run-level taxonomy aggregate. `grep -rn "TaxonomySummary" fourseer/
tests/` returns no matches. The Cycle 8 briefing specifies the fields:
- `cycle_count: int` — total classifications.
- `mode_counts: dict[str, int]` — a count per failure-mode tag that is present
  (keys drawn from the closed `mode` set; absent modes omitted).
- `gate_counts: dict[str, int]` — count of `gate == "green"` / `gate == "red"`;
  cycles with `gate is None` are NOT counted here.
- `gate_unknown: int` — count of `gate is None`.
- `merged_counts: dict[str, int]` — count of `merged is True` / `merged is
  False` as the keys `"merged"` / `"not_merged"`; cycles with `merged is None`
  are NOT counted here.
- `merged_unknown: int` — count of `merged is None`.

## Impact
Without `TaxonomySummary` there is no place to hold the run-level distribution
that `summarize_taxonomy` (TICKET-035) must return. The final Taxonomy cycle
(cycle 8) cannot be built.

## Suggestion
In `fourseer/models.py`, add a `@dataclass(frozen=True) class TaxonomySummary`
with the six fields above, each with a per-field docstring (matching the style of
`RunSummary` / `CycleClassification`). Document the invariants
`gate_counts` + `gate_unknown == cycle_count` and `merged_counts` +
`merged_unknown == cycle_count`, and that `sum(mode_counts.values()) ==
cycle_count`. Pure value object: no I/O, no side effects, stdlib-only. Add
`TaxonomySummary` to the module docstring's model list.
