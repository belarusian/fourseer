# TICKET-006: Define `Run` frozen dataclass in `fourseer/models.py`

## Title
Add a `Run` aggregate dataclass that composes the four parser outputs into a single value object.

## Evidence
`fourseer/models.py` currently defines six dataclasses (`Trajectory`, `CycleRecord`,
`BuildOrderRow`, `CycleBlock`, `GateLog`, `CommitRecord`) but has NO top-level
aggregate that groups all four parser outputs together. The four parsers
(`load_trajectories`, `parse_cycles_out`, `parse_gate_log`, `read_git_history`)
each return independent lists/objects. There is no single object a consumer
(report / taxonomy / drift) can hold that represents "one complete run of the
outer loop."

The seed dataset (`/home/sasha/AI/fourseer/seed`) contains exactly the four
artifact types:
- `trajectories/` — 44 JSON files
- `cycles.out` — 22 cycle headers (cycles 7–28)
- `gate-log.md` — Build Order table + 26 cycle blocks
- git history — from the fourseer repo itself

## Impact
Without a `Run` aggregate, every downstream consumer must call all four
parsers independently and manage the four results as separate variables. This
makes the public API awkward, prevents a single `fourseer.load_run(seed_dir)`
call, and forces consumers to re-derive the join between cycles and
trajectories (via `trajectory_path`) on their own.

## Suggestion
Add to `fourseer/models.py`: