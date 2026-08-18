# TICKET-030: Capture the gate-log Results table (gate/merged) into `CycleBlock`

## Title
Extend `CycleBlock` (models) and `parse_gate_log` (parser) to capture the
`### Results` table's `Gate (build+test+lint)` and `Merged on main` rows, so the
taxonomy can enrich a classification with `gate` / `merged`.

## Evidence
`fourseer/parse/gate_log.py` explicitly IGNORES the `### Results` table (module
docstring: "free-form prose (`### What We Did`, `### Results`) is ignored").
`CycleBlock` (models.py) has no field for the gate status or merge state. Yet
the Cycle 7 briefing requires `classify_cycle` to read, from the matching
`CycleBlock`, the gate **After** status and the `Merged on main` row. That data
is currently discarded at parse time, so it is unreachable from a `GateLog`.

Seed format (grounded): each `### Results` table carries
`| Gate (build+test+lint) | <Before> | <After> |` and
`| Merged on main | — | <hash> (PR #N) |`. The seed's gate After is GREEN for
every cycle with a Results table (cycle 1's Before was RED).

## Impact
Without capturing these rows, `gate` / `merged` can never be populated from the
gate log — the taxonomy's best-effort enrichment is impossible. This is the
enabling change for TICKET-031.

## Suggestion
Add two optional fields to `CycleBlock`: `gate_after: str | None = None` (the
Results table's `Gate (build+test+lint)` After cell, lowercased to
`"green"`/`"red"` when present) and `merged: bool | None = None` (`True` when
the `Merged on main` After cell carries a hash/PR, `False` when it is `—`/empty,
`None` when the row is absent). Extend `parse_gate_log` to scan each cycle block
for the `### Results` table and populate these two fields (tolerant: a block
with no Results table leaves both `None`). Keep the change backward-compatible
(trailing defaulted fields) so existing `CycleBlock(...)` constructor calls and
tests stay valid.
