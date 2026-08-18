# TICKET-002: Trajectory loader (tolerant of missing/extra keys)

## Title
`fourseer/parse/trajectories.py` — `load_trajectories(path) -> list[Trajectory]`.

## Evidence
The seed `trajectories/` dir holds 44 `trajectory_NNNN.json` files, each
`{"outcome": str, "messages": [{role, content}, ...]}`. Observed outcomes:
`exit:task_complete` (25), `max_steps_reached` (17), plus two error strings
(`execution_error: embedded null byte`, a long `repeated_format_error: ...`).
`step_count` is never present in the file — it must be derived as
`len(messages)`. The loader must tolerate missing/extra keys and skip corrupt
files without aborting the whole load.

## Impact
Trajectories are the primary per-cycle step-count + outcome source. A brittle
loader that crashes on one malformed file or a missing key would make the whole
report pipeline non-deterministic / non-robust.

## Suggestion
`load_trajectories(path)` accepts a directory (scanned in sorted filename order
for determinism) or a single `.json` file. For each decoded dict:
- missing `outcome` → `None`; non-str → `str(...)`;
- missing/non-list `messages` → `[]`; keep only dict entries;
- missing/non-int `step_count` → `len(messages)`; explicit int honored;
- skip files that are not valid JSON or not a dict.
Pure, stdlib-only (json, pathlib).

## Tests
`tests/test_parse_trajectories.py`:
- inline fixture dir with 2-3 small JSON files (one missing `outcome`, one with
  explicit `step_count`, one with extra keys) → assert derived values + order.
- a corrupt (non-JSON) file is skipped, not raised.
- one test against the real seed: `len == 44`, first outcome
  `max_steps_reached`, first `step_count == 122`.
