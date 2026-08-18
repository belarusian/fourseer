"""Top-level loader: compose the four parsers into a single :class:`~fourseer.models.Run`.

:func:`load_run` is the primary public entry point of the library. Given an
AI-artifact directory (the layout produced by the fourseer runner) it reads the
three on-disk artifacts and, optionally, a git repository, and returns one
:class:`~fourseer.models.Run` value object.

Layout expected under *ai_dir*::

    <ai_dir>/trajectories/*.json   -> list[Trajectory]   (load_trajectories)
    <ai_dir>/cycles.out            -> list[CycleRecord]  (parse_cycles_out)
    <ai_dir>/gate-log.md           -> GateLog            (parse_gate_log)

The git history is read from *repo_path* (a separate path) only when it is
supplied; otherwise ``Run.commits`` is empty.

Tolerance
---------
Missing optional files yield empty results rather than raising:

- a missing ``trajectories/`` directory -> ``trajectories == []``
- a missing ``cycles.out``              -> ``cycles == []``
- a missing ``gate-log.md``             -> ``gate_log == GateLog()``
- a missing/omitted *repo_path*         -> ``commits == []``

Only a *present but unreadable* git repo raises (via
:func:`fourseer.parse.git_history.read_git_history`), since a caller that
explicitly passed a repo path is asking for its history.
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


def load_run(ai_dir: str | Path, repo_path: str | Path | None = None) -> Run:
    """Load a complete run from an AI-artifact directory.

    Parameters
    ----------
    ai_dir:
        Directory containing the ``trajectories/`` subdirectory, ``cycles.out``
        and ``gate-log.md``. Missing optional files yield empty results.
    repo_path:
        Optional path to a git working tree. When given, its commit history is
        read into ``Run.commits``; when ``None`` (the default) ``commits`` is
        empty.

    Returns
    -------
    Run
        The composed aggregate of all four parser outputs.
    """
    ai = Path(ai_dir)

    # load_trajectories tolerates a missing directory (glob yields nothing).
    trajectories = load_trajectories(ai / "trajectories")

    cycles_text = _read_optional_text(ai / "cycles.out")
    cycles = parse_cycles_out(cycles_text) if cycles_text is not None else []

    gate_text = _read_optional_text(ai / "gate-log.md")
    gate_log = parse_gate_log(gate_text) if gate_text is not None else GateLog()

    commits = read_git_history(repo_path) if repo_path is not None else []

    return Run(
        trajectories=trajectories,
        cycles=cycles,
        gate_log=gate_log,
        commits=commits,
    )
