# TICKET-008: Export `Run` and `load_run` from `fourseer/__init__.py`

## Title
Add `Run` to the model re-exports and `load_run` to the parser re-exports in
the package's public `__init__.py`.

## Evidence
`fourseer/__init__.py` (lines 1–38) currently re-exports:
- Models: `BuildOrderRow`, `CommitRecord`, `CycleBlock`, `CycleRecord`, `GateLog`, `Trajectory`
- Parsers: `load_trajectories`, `parse_cycles_out`, `parse_gate_log`, `read_git_history`

Neither `Run` (TICKET-006) nor `load_run` (TICKET-007) is exported. The
`__all__` list (lines 22–38) does not include them. A consumer writing
`from fourseer import Run, load_run` would get an `ImportError`.

## Impact
The primary public API of the library — "load a run, get a Run" — is not
accessible through the package root. Consumers must reach into submodules
(`from fourseer.models import Run`, `from fourseer.load import load_run`),
which contradicts the documented public surface in the module docstring
("Public surface is re-exported here").

## Suggestion
In `fourseer/__init__.py`:
1. Add `Run` to the `from fourseer.models import (...)` block.
2. Add `from fourseer.load import load_run`.
3. Add `"Run"` and `"load_run"` to `__all__`.
4. Update the module docstring's submodule list to include
   `- fourseer.load : top-level loader (composes the four parsers into a Run)`.

## Tests
`tests/test_smoke.py`: add `from fourseer import Run, load_run` at the top;
assert both are importable.
