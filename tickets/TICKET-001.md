# TICKET-001: Typed data models for parsed artifacts

## Title
`fourseer/models.py` — pure, stdlib-only dataclasses for the parsed domain.

## Evidence
The package needs a canonical set of value objects that every parser produces
and every consumer (report / taxonomy / drift) consumes. The seed dataset
(`/home/sasha/AI/fourseer/seed`) defines the shapes:
- `trajectories/*.json` → `{"outcome": str, "messages": [{role, content}, ...]}`
  (44 files; `step_count` is NOT in the file, must be derived from `len(messages)`).
- `cycles.out` → `========== CYCLE N  HH:MM:SSZ ==========` headers, each
  optionally followed by `OUTER trajectory saved to:` + `OUTER outcome:` lines.
  Wall-clock-killed cycles (seed cycles 21, 22, 25) write NO OUTER lines.
- `gate-log.md` → a `## Build Order` markdown table (Phase | Cycles | Target)
  and one `## Cycle N` block per cycle (Date, HEAD start/end, Lessons).
- `git log` → timestamped commits for duration.

## Impact
Without typed models the parsers have no stable contract and downstream
report/taxonomy/drift cycles cannot join the four sources deterministically.

## Suggestion
Define frozen dataclasses in `fourseer/models.py`:
- `Trajectory(outcome: Optional[str], messages: list[dict], step_count: int)`
- `CycleRecord(cycle_no: int, timestamp: str, outcome: Optional[str], trajectory_path: Optional[str])`
- `BuildOrderRow(phase: str, cycles: str, target: str)`
- `CycleBlock(cycle_no: int, title: str, date: Optional[str], head_start: Optional[str], head_end: Optional[str], lessons: list[str])`
- `GateLog(build_order: list[BuildOrderRow], cycles: list[CycleBlock])`
- `CommitRecord(hash: str, short_hash: str, author: str, date: str, subject: str)`
Pure data, no I/O. Re-export from `fourseer/__init__.py`.

## Tests
`tests/test_models.py`: construct each model, assert field defaults, assert
frozen-ness (mutation raises), assert `GateLog`/`CycleBlock` list defaults.
