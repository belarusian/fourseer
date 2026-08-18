"""Artifact parsers for fourseer.

Each submodule is a pure, deterministic, stdlib-only function that turns one
kind of on-disk artifact into the typed models from :mod:`fourseer.models`:

- :mod:`fourseer.parse.trajectories` — ``trajectories/*.json`` -> ``list[Trajectory]``
- :mod:`fourseer.parse.cycles_out`   — ``cycles.out`` text -> ``list[CycleRecord]``
- :mod:`fourseer.parse.gate_log`     — gate-log markdown -> ``GateLog``
- :mod:`fourseer.parse.git_history`  — a git repo -> ``list[CommitRecord]``

Parsers never mutate their inputs and never write; they only read and return
new model instances.
"""

from fourseer.parse.cycles_out import parse_cycles_out
from fourseer.parse.gate_log import parse_gate_log
from fourseer.parse.git_history import read_git_history
from fourseer.parse.trajectories import load_trajectories

__all__ = [
    "load_trajectories",
    "parse_cycles_out",
    "parse_gate_log",
    "read_git_history",
]
