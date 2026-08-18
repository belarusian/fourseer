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

import re
from pathlib import PurePosixPath

from fourseer.models import CycleMetrics, Run, Trajectory

__all__ = ["build_cycle_metrics", "extract_tokens_cost", "render_report"]

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


# A conservative, line-anchored usage record: a line that is itself of the form
# ``usage: tokens=<int> [cost=<float>]``. Line-anchored (``^``/``$``) so that
# incidental prose — a shell ``usage()`` function, TypeScript ``prompt_tokens:
# number;`` type declarations, or the word "usage" inside a comment — never
# matches. ``tokens=<int>`` is required; ``cost=<float>`` is optional.
_USAGE_RE = re.compile(
    r"^\s*usage\s*:\s*tokens=(\d+)(?:\s+cost=([0-9]*\.?[0-9]+))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# The single stable placeholder for a missing value in the rendered table.
_PLACEHOLDER = "-"


def render_report(metrics: list[CycleMetrics]) -> str:
    """Render per-cycle metrics as a deterministic markdown table.

    The output is a pure, deterministic, stdlib-only string transformation of
    *metrics*:

    - a header line ``# Per-Cycle Metrics (N cycles)`` where ``N`` is
      ``len(metrics)``;
    - a markdown table with columns ``Cycle | Outcome | Steps | Duration (s) |
      Trajectory``;
    - one row per metric, in the GIVEN order (the caller passes the already-
      sorted :func:`build_cycle_metrics` output); the renderer does NOT re-sort;
    - a ``None`` value (a kill's ``outcome``/``trajectory_name``, or the last
      cycle's ``duration_seconds``) renders as the single stable placeholder
      ``-`` so the table stays aligned and stable.

    Parameters
    ----------
    metrics:
        The per-cycle metrics to render. The function never mutates it.

    Returns
    -------
    str
        The rendered report (header + table), ending with a trailing newline.
    """
    lines: list[str] = [
        f"# Per-Cycle Metrics ({len(metrics)} cycles)",
        "",
        "| Cycle | Outcome | Steps | Duration (s) | Trajectory |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in metrics:
        outcome = m.outcome if m.outcome is not None else _PLACEHOLDER
        duration = (
            str(m.duration_seconds) if m.duration_seconds is not None else _PLACEHOLDER
        )
        trajectory = m.trajectory_name if m.trajectory_name is not None else _PLACEHOLDER
        lines.append(
            f"| {m.cycle_no} | {outcome} | {m.step_count} | {duration} | {trajectory} |"
        )
    return "\n".join(lines) + "\n"


def extract_tokens_cost(
    trajectory: Trajectory,
) -> tuple[int | None, float | None]:
    """Extract ``(tokens, cost)`` from a trajectory's message content.

    Scans each message's ``content`` for an explicit, unambiguous usage record
    (see :data:`_USAGE_RE`). The match is conservative and line-anchored, so
    incidental prose (a shell ``usage()`` function, TypeScript
    ``prompt_tokens: number;`` type declarations, or the word "usage" in a
    comment) never matches. When no record is present — the seed case, and any
    trajectory without structured usage data — returns ``(None, None)``.

    If multiple records are present, ``tokens`` is the sum of their token
    counts and ``cost`` is the sum of their costs (deterministic, in message
    order). ``cost`` is ``None`` when no record carries a cost figure.

    Parameters
    ----------
    trajectory:
        The trajectory to scan. The function never mutates it.

    Returns
    -------
    tuple[int | None, float | None]
        ``(tokens, cost)``; either or both may be ``None``.
    """
    total_tokens: int | None = None
    total_cost: float | None = None
    for message in trajectory.messages:
        content = message.get("content")
        if not isinstance(content, str):
            continue
        for match in _USAGE_RE.finditer(content):
            tokens = int(match.group(1))
            if total_tokens is None:
                total_tokens = tokens
            else:
                total_tokens += tokens
            cost_raw = match.group(2)
            if cost_raw is not None:
                cost = float(cost_raw)
                total_cost = cost if total_cost is None else total_cost + cost
    return total_tokens, total_cost
