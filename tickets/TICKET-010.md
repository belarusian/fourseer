# TICKET-010: Record trajectory basename on `Trajectory` + populate in loader

## Title
Add a `name: str = ""` field to `Trajectory` and have
`load_trajectories` populate it from the source filename, so the validator can
match `CycleRecord.trajectory_path` basenames against loaded trajectories.

## Evidence
Check (a) of the consistency layer requires: "each `CycleRecord.trajectory_path`
(when set) must correspond to a loaded trajectory (match on the basename
`trajectory_NNNN.json`)". But `Trajectory` currently has only `outcome`,
`messages`, `step_count` — no identity. The loader (`fourseer/parse/trajectories.py`)
reads each file but discards the filename, so there is no way to know which
loaded trajectory is `trajectory_0013.json`.

## Impact
Without a name on `Trajectory`, the validator cannot correlate a cycle's
referenced trajectory path with the set of loaded trajectories, and check (a)
(orphan trajectory path detection) is impossible.

## Suggestion
- `fourseer/models.py`: add `name: str = ""` to `Trajectory` (a trailing field
  with a default keeps every existing constructor call valid — backward
  compatible). Document it as the source filename (basename) or `""`.
- `fourseer/parse/trajectories.py`: in `load_trajectories`, pass each file's
  `f.name` into the constructed `Trajectory` (both the single-file and
  directory-scan paths).

## Tests
`tests/test_parse_trajectories.py`: assert loaded trajectories carry the correct
`name` (basename) for the inline fixture dir and the single-file case; existing
tests (which omit `name`) must still pass unchanged.
