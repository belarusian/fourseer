"""Cross-source consistency validation for a :class:`~fourseer.models.Run`.

:func:`validate_run` is a pure, deterministic, stdlib-only function that
cross-checks the four independently-parsed sources in a :class:`Run` and
returns a stable, sorted list of :class:`~fourseer.models.ConsistencyIssue`
objects describing every disagreement it finds.

It performs no I/O, never mutates its input, and returns ``[]`` when the run
is internally consistent. The checks are:

- (a) ``orphan_trajectory_path`` — a ``CycleRecord.trajectory_path`` (when set)
  whose basename is not among the loaded ``Trajectory.name`` values.
- (b) ``cycle_not_in_gate_log`` — a ``CycleRecord.cycle_no`` with no matching
  ``CycleBlock.cycle_no`` in the gate log.
- (b') ``gate_cycle_not_in_cycles_out`` — a ``CycleBlock.cycle_no`` with no
  matching ``CycleRecord.cycle_no`` in ``cycles.out``.
- (c) ``build_order_range_gap`` — an executed ``CycleRecord.cycle_no`` that
  falls outside every Build Order range.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from fourseer.models import ConsistencyIssue, Run

__all__ = ["validate_run"]


def _parse_range(cycles: str) -> tuple[int, int] | None:
    """Parse a Build Order ``cycles`` string into an inclusive ``(lo, hi)`` range.

    Accepts a single number (``"7"`` -> ``(7, 7)``) or a range (``"1-3"`` ->
    ``(1, 3)``). Returns ``None`` when the string is not a recognizable range.
    """
    s = cycles.strip()
    if not s:
        return None
    if "-" in s:
        lo_s, _, hi_s = s.partition("-")
        try:
            lo, hi = int(lo_s.strip()), int(hi_s.strip())
        except ValueError:
            return None
        if lo > hi:
            lo, hi = hi, lo
        return (lo, hi)
    try:
        n = int(s)
    except ValueError:
        return None
    return (n, n)


def validate_run(run: Run) -> list[ConsistencyIssue]:
    """Cross-check the four sources in *run* and return their disagreements.

    Parameters
    ----------
    run:
        The aggregate to validate. The function never mutates it.

    Returns
    -------
    list[ConsistencyIssue]
        One issue per detected inconsistency, sorted by the stable key
        ``(code, cycle_no or -1, detail)``. Empty when the run is consistent.
    """
    issues: list[ConsistencyIssue] = []

    # (a) orphan_trajectory_path: each referenced trajectory basename must be
    #     among the loaded trajectory names.
    loaded_names = {t.name for t in run.trajectories}
    for rec in run.cycles:
        if rec.trajectory_path is None:
            continue
        base = PurePosixPath(rec.trajectory_path).name
        if base not in loaded_names:
            issues.append(
                ConsistencyIssue(
                    code="orphan_trajectory_path",
                    cycle_no=rec.cycle_no,
                    detail=(
                        f"cycle {rec.cycle_no} references trajectory "
                        f"'{base}' which is not among the loaded trajectories"
                    ),
                )
            )

    # (b) cycle_not_in_gate_log: a cycle record with no matching gate block.
    gate_cycle_nos = {b.cycle_no for b in run.gate_log.cycles}
    for rec in run.cycles:
        if rec.cycle_no not in gate_cycle_nos:
            issues.append(
                ConsistencyIssue(
                    code="cycle_not_in_gate_log",
                    cycle_no=rec.cycle_no,
                    detail=f"cycle {rec.cycle_no} has no matching gate-log block",
                )
            )

    # (b') gate_cycle_not_in_cycles_out: a gate block with no matching record.
    record_cycle_nos = {r.cycle_no for r in run.cycles}
    for block in run.gate_log.cycles:
        if block.cycle_no not in record_cycle_nos:
            issues.append(
                ConsistencyIssue(
                    code="gate_cycle_not_in_cycles_out",
                    cycle_no=block.cycle_no,
                    detail=f"gate-log cycle {block.cycle_no} has no cycles.out record",
                )
            )

    # (c) build_order_range_gap: an executed cycle outside every planned range.
    ranges = [r for r in (_parse_range(row.cycles) for row in run.gate_log.build_order) if r]
    for rec in run.cycles:
        if not any(lo <= rec.cycle_no <= hi for lo, hi in ranges):
            issues.append(
                ConsistencyIssue(
                    code="build_order_range_gap",
                    cycle_no=rec.cycle_no,
                    detail=f"cycle {rec.cycle_no} is outside every Build Order range",
                )
            )

    issues.sort(key=lambda i: (i.code, i.cycle_no if i.cycle_no is not None else -1, i.detail))
    return issues
