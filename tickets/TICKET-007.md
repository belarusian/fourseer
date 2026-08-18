# TICKET-007: Implement `load_run()` top-level loader in `fourseer/load.py`

## Title
Create `fourseer/load.py` with a `load_run(seed_dir) -> Run` function that
composes all four parsers into a single `Run` aggregate.

## Evidence
No `fourseer/load.py` exists. The four parsers live in `fourseer/parse/`:
- `fourseer/parse/trajectories.py` → `load_trajectories(path) -> list[Trajectory]`
- `fourseer/parse/cycles_out.py` → `parse_cycles_out(text) -> list[CycleRecord]`
- `fourseer/parse/gate_log.py` → `parse_gate_log(text) -> GateLog`
- `fourseer/parse/git_history.py` → `read_git_history(repo_path) -> list[CommitRecord]`

The seed directory layout is: