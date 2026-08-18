"""Per-cycle metrics for a :class:`~fourseer.models.Run`.

:func:`build_cycle_metrics` is a pure, deterministic, stdlib-only function. It
joins each :class:`~fourseer.models.CycleRecord` with the
:class:`~fourseer.models.Trajectory` it references (by trajectory basename) and
derives the wall-clock duration of each cycle from the gap between that cycle's
start timestamp and the next cycle's start timestamp (with a midnight wrap).

It performs no I/O, never mutates its input, and returns a list sorted by
``cycle_no``.

:func:`summarize_run` rolls those per-cycle metrics up into a single
:class:`~fourseer.models.RunSummary` (run-level totals), and
:func:`render_summary` renders that aggregate as a short, deterministic
human-readable block. Both are pure, deterministic, stdlib-only, and
perform no I/O.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from fourseer.models import CycleMetrics, Run, RunSummary, Trajectory

__all__ = [
    "build_cycle_metrics",
    "extract_tokens_cost",
    "render_report",
    "render_summary",
    "summarize_run",
]

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

def summarize_run(
    metrics: list[CycleMetrics],
    trajectories: list[Trajectory] | None = None,
) -> RunSummary:
    """Roll per-cycle :class:`~fourseer.models.CycleMetrics` up into a
    :class:`~fourseer.models.RunSummary`.

    A pure, deterministic, stdlib-only aggregation. It performs no I/O and
    never mutates *metrics* or *trajectories*.

    Counts and sums
    ---------------
    - ``cycle_count`` is ``len(metrics)``;
    - ``completed_count`` is the number of metrics whose ``outcome`` is
      non-``None``;
    - ``killed_count`` is the number of metrics whose ``outcome`` is ``None``
      (so ``completed_count + killed_count == cycle_count``);
    - ``total_steps`` is the sum of every metric's ``step_count``;
    - ``total_duration_seconds`` is the sum of the non-``None``
      ``duration_seconds`` values (``0`` when none);
    - ``cycles_with_duration`` is the count of non-``None`` durations.

    Tokens / cost (the load-bearing join)
    -------------------------------------
    ``total_tokens`` / ``total_cost`` are computed by joining on the metrics'
    ``trajectory_name`` field — the set of trajectories the run's cycles
    actually reference — NOT by scanning every entry of *trajectories*:

    - a ``name -> Trajectory`` map is built from the supplied *trajectories*;
    - the DISTINCT referenced ``trajectory_name`` values are collected (a name
      referenced by two cycles is counted ONCE);
    - :func:`extract_tokens_cost` is called on each distinct referenced
      trajectory and the results are summed.

    ``total_tokens`` / ``total_cost`` are ``None`` unless at least one joined
    trajectory carries a usage record. When *trajectories* is ``None`` (or no
    referenced trajectory is present in it) both are ``None``. A trajectory
    present in *trajectories* but referenced by no cycle contributes nothing.

    Parameters
    ----------
    metrics:
        The per-cycle metrics to aggregate (typically the output of
        :func:`build_cycle_metrics`). Never mutated.
    trajectories:
        The loaded trajectories to join against, or ``None``. When ``None``
        (or when no referenced trajectory is present) ``total_tokens`` /
        ``total_cost`` are ``None``. Never mutated.

    Returns
    -------
    RunSummary
        The run-level aggregate.
    """
    cycle_count = len(metrics)
    completed_count = sum(1 for m in metrics if m.outcome is not None)
    killed_count = cycle_count - completed_count
    total_steps = sum(m.step_count for m in metrics)
    total_duration_seconds = sum(
        m.duration_seconds for m in metrics if m.duration_seconds is not None
    )
    cycles_with_duration = sum(1 for m in metrics if m.duration_seconds is not None)

    total_tokens: int | None = None
    total_cost: float | None = None
    if trajectories is not None:
        by_name: dict[str, Trajectory] = {t.name: t for t in trajectories}
        # Distinct referenced names, in first-seen order (deterministic).
        referenced: list[str] = []
        seen: set[str] = set()
        for m in metrics:
            name = m.trajectory_name
            if name is not None and name not in seen:
                seen.add(name)
                referenced.append(name)
        for name in referenced:
            traj = by_name.get(name)
            if traj is None:
                continue
            tokens, cost = extract_tokens_cost(traj)
            if tokens is not None:
                total_tokens = tokens if total_tokens is None else total_tokens + tokens
            if cost is not None:
                total_cost = cost if total_cost is None else total_cost + cost

    return RunSummary(
        cycle_count=cycle_count,
        completed_count=completed_count,
        killed_count=killed_count,
        total_steps=total_steps,
        total_duration_seconds=total_duration_seconds,
        cycles_with_duration=cycles_with_duration,
        total_tokens=total_tokens,
        total_cost=total_cost,
    )


def render_summary(summary: RunSummary) -> str:
    """Render a :class:`~fourseer.models.RunSummary` as a short block.

    A pure, deterministic, stdlib-only string transformation, consistent in
    style with :func:`render_report`:

    - a header line ``# Run Summary (N cycles)`` where ``N`` is
      ``summary.cycle_count``;
    - one ``key: value`` line per aggregate field, in a fixed order;
    - a ``None`` ``total_tokens`` / ``total_cost`` renders as the single
      stable placeholder ``-`` (see :data:`_PLACEHOLDER`).

    Parameters
    ----------
    summary:
        The run-level aggregate to render. Never mutated.

    Returns
    -------
    str
        The rendered summary block, ending with a trailing newline.
    """
    tokens = (
        str(summary.total_tokens) if summary.total_tokens is not None else _PLACEHOLDER
    )
    cost = str(summary.total_cost) if summary.total_cost is not None else _PLACEHOLDER
    lines: list[str] = [
        f"# Run Summary ({summary.cycle_count} cycles)",
        "",
        f"cycles: {summary.cycle_count}",
        f"completed: {summary.completed_count}",
        f"killed: {summary.killed_count}",
        f"total steps: {summary.total_steps}",
        f"total duration (s): {summary.total_duration_seconds}",
        f"cycles with duration: {summary.cycles_with_duration}",
        f"total tokens: {tokens}",
        f"total cost: {cost}",
    ]
    return "\n".join(lines) + "\n"
