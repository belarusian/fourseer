"""Per-cycle metrics for a :class:`~fourseer.models.Run`.

:func:`build_cycle_metrics` is a pure, deterministic, stdlib-only function. It
joins each :class:`~fourseer.models.CycleRecord` with the
:class:`~fourseer.models.Trajectory` it references (by trajectory basename) and
derives the wall-clock duration of each cycle from the gap between that cycle's
start timestamp and the next cycle's start timestamp (with a midnight wrap).

It performs no I/O, never mutates its input, and returns a list sorted by
``cycle_no``.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from fourseer.models import CycleMetrics, Run, Trajectory

__all__ = ["build_cycle_metrics"]

_SECONDS_PER_DAY = 86400


def _timestamp_to_seconds(ts: str) -> int:
    """Convert an ``HH:MM:SSZ`` wall-clock timestamp to seconds since midnight.

    Manual integer math (no ``datetime``) so the parse is trivially pure and
    deterministic. The trailing ``Z`` (UTC marker) is dropped.
    """
    body = ts[:-1] if ts.endswith("Z") else ts
    h, m, s = body.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def build_cycle_metrics(run: Run) -> list[CycleMetrics]:
    """Build per-cycle :class:`~fourseer.models.CycleMetrics` for *run*.

    For each :class:`~fourseer.models.CycleRecord` in ``run.cycles`` (file
    order):

    - the trajectory is joined by matching
      ``PurePosixPath(trajectory_path).name`` against the loaded
      ``Trajectory.name`` set; a cycle whose ``trajectory_path`` is ``None``
      (a wall-clock kill) joins no trajectory;
    - ``step_count`` is the joined trajectory's ``step_count`` (``0`` when no
      trajectory is joined);
    - ``trajectory_name`` is the joined ``Trajectory.name`` (``None`` when no
      trajectory is joined);
    - ``duration_seconds`` is the seconds between this cycle's start timestamp
      and the NEXT cycle's start timestamp in file order, with a midnight wrap
      (a negative raw difference has ``86400`` added); the last cycle in file
      order has no following start, so its ``duration_seconds`` is ``None``.

    Parameters
    ----------
    run:
        The aggregate to build metrics for. The function never mutates it.

    Returns
    -------
    list[CycleMetrics]
        One metric per cycle, sorted by ``cycle_no``.
    """
    # Map trajectory basename -> Trajectory for O(1) joins.
    by_name: dict[str, Trajectory] = {}
    for t in run.trajectories:
        by_name[t.name] = t

    cycles = run.cycles
    n = len(cycles)
    metrics: list[CycleMetrics] = []

    for i, rec in enumerate(cycles):
        # Join trajectory by basename; a kill (trajectory_path None) joins none.
        step_count = 0
        trajectory_name: str | None = None
        if rec.trajectory_path is not None:
            base = PurePosixPath(rec.trajectory_path).name
            traj = by_name.get(base)
            if traj is not None:
                step_count = traj.step_count
                trajectory_name = traj.name

        # Duration: gap to the next cycle's start, midnight-wrapped.
        duration_seconds: int | None = None
        if i + 1 < n:
            raw = _timestamp_to_seconds(cycles[i + 1].timestamp) - _timestamp_to_seconds(
                rec.timestamp
            )
            if raw < 0:
                raw += _SECONDS_PER_DAY
            duration_seconds = raw

        metrics.append(
            CycleMetrics(
                cycle_no=rec.cycle_no,
                outcome=rec.outcome,
                step_count=step_count,
                duration_seconds=duration_seconds,
                trajectory_name=trajectory_name,
            )
        )

    metrics.sort(key=lambda m: m.cycle_no)
    return metrics
