"""Parse ``trajectories/*.json`` files into :class:`~fourseer.models.Trajectory`.

The on-disk format is a JSON object with at least ``outcome`` (str) and
``messages`` (list of ``{role, content, ...}`` dicts). Real files carry only
those two keys, but the loader is deliberately tolerant:

- a missing ``outcome`` becomes ``None``;
- a missing ``messages`` becomes ``[]``;
- a missing ``step_count`` is derived as ``len(messages)``;
- an explicit ``step_count`` (int) is honored when present;
- extra top-level keys and extra per-message keys are ignored;
- each trajectory's ``name`` is set to the source file's basename (``f.name``).

The loader is pure and deterministic: it reads files in sorted filename order
so the returned list is stable across runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from fourseer.models import Trajectory

__all__ = ["load_trajectories"]


def load_trajectories(path: str | Path) -> list[Trajectory]:
    """Load every ``*.json`` trajectory under *path* into a list of
    :class:`~fourseer.models.Trajectory`.

    Parameters
    ----------
    path:
        A directory containing ``trajectory_NNNN.json`` files, or a single
        ``.json`` file. A directory is scanned in sorted filename order; a
        single file yields a one-element list.

    Returns
    -------
    list[Trajectory]
        One trajectory per JSON file, in deterministic (sorted) order.

    Notes
    -----
    Files that are not valid JSON are skipped silently so that a single
    corrupt artifact does not abort the whole load.
    """
    p = Path(path)
    if p.is_file():
        files = [p]
    else:
        files = sorted(p.glob("*.json"))

    out: list[Trajectory] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        out.append(_to_trajectory(data, name=f.name))
    return out


def _to_trajectory(data: dict, *, name: str = "") -> Trajectory:
    """Build a :class:`Trajectory` from one decoded JSON object, tolerating
    missing/extra keys.

    Parameters
    ----------
    data:
        The decoded JSON object.
    name:
        The source filename (basename) to record on the trajectory, or ``""``.
    """
    outcome = data.get("outcome")
    if outcome is not None and not isinstance(outcome, str):
        outcome = str(outcome)

    messages = data.get("messages")
    if not isinstance(messages, list):
        messages = []
    # Keep only dict messages; ignore malformed entries.
    messages = [m for m in messages if isinstance(m, dict)]

    step_count = data.get("step_count")
    if isinstance(step_count, int):
        step_count = step_count
    else:
        step_count = len(messages)

    return Trajectory(outcome=outcome, messages=messages, step_count=step_count, name=name)
