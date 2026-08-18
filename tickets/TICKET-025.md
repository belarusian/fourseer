# TICKET-025: Add `summarize_run(metrics, trajectories=None) -> RunSummary`

## Title
Add `summarize_run` to `fourseer/report.py` that rolls per-cycle `CycleMetrics`
up into a `RunSummary`, joining trajectories by `trajectory_name` for tokens/cost.

## Evidence
`fourseer/report.py` (209 lines) has `build_cycle_metrics` (line 36),
`render_report` (line 123), and `extract_tokens_cost` (line 167), but no
`summarize_run`. `__all__` (line 20) is
`["build_cycle_metrics", "extract_tokens_cost", "render_report"]`.

JOIN SEMANTICS (the load-bearing decision). The seed has **44** trajectories
(`ls seed/trajectories | wc -l` = 44) but only **19** are referenced by the 22
cycles' `trajectory_path` basenames. Two cycles reference the SAME trajectory:
`trajectory_0043.json` is the `trajectory_path` basename for BOTH cycle 8 and
cycle 28 (see `seed/cycles.out`). Therefore the join must be driven by the
metrics' `trajectory_name` field (the set of trajectories the run's cycles
actually reference), NOT by scanning every entry of the supplied
`trajectories` list. Consequences to pin:
- A trajectory present in `trajectories` but referenced by no cycle must NOT
  contribute to `total_tokens` / `total_cost` (else the 25 unreferenced seed
  trajectories would be over-counted).
- A trajectory referenced by two cycles contributes its tokens/cost ONCE (the
  join is over the set of referenced names, not per-cycle).

## Impact
`summarize_run` is the core of the run-level summary. Getting the join wrong
(either scanning all trajectories, or summing per-cycle) silently inflates
`total_tokens` / `total_cost` and breaks the "None when no usage data" contract
for the seed (seed carries no usage records, so both must be `None`).

## Suggestion
In `fourseer/report.py`, add: