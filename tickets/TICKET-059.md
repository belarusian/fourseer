# TICKET-059 — taxonomy: landed/lost distribution + render line

## Problem
The run-level `TaxonomySummary` / `render_taxonomy` (cycle 8) has no landed/lost
dimension, so the CLI cannot report how many cycles landed vs lost work.

## Target
- `fourseer/models.py`: extend `TaxonomySummary` with a backward-compatible trailing
  field `landed_counts: dict[str, int] = field(default_factory=dict)` (keys from the
  closed set `"landed"` / `"lost"` / `"unknown"`) and `landed_unknown: int = 0` for
  classifications whose `landed is None`. Document the invariant
  `sum(landed_counts.values()) + landed_unknown == cycle_count`.
- `fourseer/taxonomy.py`: `summarize_taxonomy` tallies `landed_counts` /
  `landed_unknown`; `render_taxonomy` adds a `landed:` line (e.g.
  `landed: landed=N, lost=N, unknown=N`) consistent in style with the existing
  `modes:` / `gates:` / `merged:` lines (sorted tags, absent tag omitted, zero count
  omitted, `-` placeholder when empty, `unknown=<n>` suffix only when non-zero).

## Acceptance
`render_taxonomy(summarize_taxonomy(classify_run(launch-gate run)))` includes a
`landed:` line with `lost>=1` (cycle 2) and `landed>=1` (cycle 5). Existing seed
taxonomy output is unchanged except for the new `landed:` line.
