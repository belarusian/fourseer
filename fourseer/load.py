"""Top-level loader: compose the four parsers into a single :class:`~fourseer.models.Run`.

:func:`load_run` is the primary public entry point of the library. Given an
AI-artifact directory it reads the on-disk artifacts and, optionally, a git
repository, and returns one :class:`~fourseer.models.Run` value object.

File discovery
--------------
The loader discovers files by pattern rather than requiring exact names:

- Gate log: ``gate-log.md``, or any ``*gate*.md`` in *ai_dir* (first match,
  preferring filenames containing ``cycle-001``).
- Cycles output: ``cycles.out`` or ``cycles*.out`` in *ai_dir*.
- Trajectories: ``trajectories/*.json`` in *ai_dir* (unchanged).

Tolerance
---------
Missing optional files yield empty results rather than raising.
"""

from __future__ import annotations

from pathlib import Path

from fourseer.models import GateLog, Run
from fourseer.parse.cycles_out import parse_cycles_out
from fourseer.parse.gate_log import parse_gate_log
from fourseer.parse.git_history import read_git_history
from fourseer.parse.trajectories import load_trajectories

__all__ = ["load_run"]


def _read_optional_text(path: Path) -> str | None:
    """Return the UTF-8 text of *path*, or ``None`` if it is not a file."""
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def _find_gate_log(ai: Path) -> Path | None:
    """Discover the gate log file in *ai*.

    Preference order:
    1. Exact ``gate-log.md`` (the normalized seed name).
    2. Any file matching ``*gate*.md``, preferring one with ``cycle-001``
       in the name.
    3. First ``*gate*.md`` match if no ``cycle-001`` candidate exists.
    """
    exact = ai / "gate-log.md"
    if exact.is_file():
        return exact

    candidates = sorted(ai.glob("*gate*.md"))
    if not candidates:
        return None

    for c in candidates:
        if "cycle-001" in c.name:
            return c
    return candidates[0]


def _find_cycles_out(ai: Path) -> Path | None:
    """Discover the cycles output file in *ai*.

    Looks for ``cycles.out`` or ``cycles*.out``. Returns the first match,
    or ``None`` if no candidate exists.
    """
    exact = ai / "cycles.out"
    if exact.is_file():
        return exact
    matches = sorted(ai.glob("cycles*.out"))
    if matches:
        return matches[0]
    return None


def load_run(ai_dir: str | Path, repo_path: str | Path | None = None) -> Run:
    """Load a complete run from an AI-artifact directory.

    Parameters
    ----------
    ai_dir:
        Directory containing the ``trajectories/`` subdirectory and the
        gate log / cycles output (discovered by pattern). Missing optional
        files yield empty results.
    repo_path:
        Optional path to a git working tree. When given, its commit history
        is read into ``Run.commits``; when ``None`` (the default) ``commits``
        is empty.

    Returns
    -------
    Run
        The composed aggregate of all four parser outputs.
    """
    ai = Path(ai_dir)

    trajectories = load_trajectories(ai / "trajectories")

    cycles_path = _find_cycles_out(ai)
    cycles_text = _read_optional_text(cycles_path) if cycles_path else None
    cycles = parse_cycles_out(cycles_text) if cycles_text is not None else []

    gate_path = _find_gate_log(ai)
    gate_text = _read_optional_text(gate_path) if gate_path else None
    gate_log = parse_gate_log(gate_text) if gate_text is not None else GateLog()

    commits = read_git_history(repo_path) if repo_path is not None else []

    return Run(
        trajectories=trajectories,
        cycles=cycles,
        gate_log=gate_log,
        commits=commits,
    )
