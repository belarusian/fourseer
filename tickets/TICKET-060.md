# TICKET-060 — report: surface landed/lost in the per-cycle metrics table + golden fixture

## Problem
The per-cycle metrics table (`render_report`) does not show the landed/lost state, and
there is no committed golden fixture that pins the lost-vs-landed distinction on a
launch-gate-dialect fragment.

## Target
- `fourseer/report.py`: extend `render_report` with an optional
  `landed_by_cycle: dict[int, str] | None = None` parameter (default keeps the existing
  signature working). When supplied, add a `Landed` column whose cell is the tag for
  that cycle's `cycle_no` (`-` when absent / mapping is None). Deterministic, no I/O.
- `fourseer/cli.py`: the `report` subcommand passes the per-cycle landed tags (from
  `classify_run`) into `render_report`.
- `tests/fixtures/`: a committed golden fixture — a minimal launch-gate-dialect
  gate-log fragment + cycles.out fragment containing one LOST cycle (cycle-2 shape:
  marker, no block, no PR) and one LANDED cycle (cycle-5 shape: marker, block with
  `PR #N ... MERGED`).

## Acceptance
`render_report(metrics, landed_by_cycle)` renders a `Landed` column; the CLI `report`
subcommand shows it. The fixture is committed under `tests/fixtures/`.
