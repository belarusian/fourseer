"""Failure-mode taxonomy for a :class:`~fourseer.models.Run`.

Each outer-loop cycle is classified into a stable failure-mode ``mode`` derived
from its :class:`~fourseer.models.CycleMetrics` ``outcome`` string, and — when
the gate log carries a matching ``### Results`` table — enriched with the cycle's
gate outcome (``gate``) and merge status (``merged``).

The closed set of ``mode`` tags is:

- ``"wall_clock_kill"`` — ``outcome is None`` (killed before writing an outcome).
- ``"max_steps"``       — ``outcome == "max_steps_reached"``.
- ``"task_complete"``   — ``outcome == "exit:task_complete"``.
- ``"execution_error"`` — ``outcome`` starts with ``"execution_error"``.
- ``"format_error"``    — ``outcome`` starts with ``"repeated_format_error"``.
- ``"other"``           — any other non-``None`` outcome.

Both :func:`classify_cycle` and :func:`classify_run` are pure, deterministic,
stdlib-only, and perform no I/O and never mutate their inputs.
"""

from __future__ import annotations

from fourseer.models import CycleClassification, CycleMetrics, GateLog, Run
from fourseer.report import build_cycle_metrics

__all__ = ["classify_cycle", "classify_run"]

# The closed, stable set of failure-mode tags (documented in the module
# docstring and on :class:`CycleClassification`).
MODE_WALL_CLOCK_KILL = "wall_clock_kill"
MODE_MAX_STEPS = "max_steps"
MODE_TASK_COMPLETE = "task_complete"
MODE_EXECUTION_ERROR = "execution_error"
MODE_FORMAT_ERROR = "format_error"
MODE_OTHER = "other"


def _mode_from_outcome(outcome: str | None) -> str:
    """Map an outcome string (or ``None``) to a closed failure-mode tag.

    The mapping is total: every possible input maps to exactly one tag.
    """
    if outcome is None:
        return MODE_WALL_CLOCK_KILL
    if outcome == "max_steps_reached":
        return MODE_MAX_STEPS
    if outcome == "exit:task_complete":
        return MODE_TASK_COMPLETE
    if outcome.startswith("execution_error"):
        return MODE_EXECUTION_ERROR
    if outcome.startswith("repeated_format_error"):
        return MODE_FORMAT_ERROR
    return MODE_OTHER


def classify_cycle(
    metrics: CycleMetrics, gate_log: GateLog | None = None
) -> CycleClassification:
    """Classify a single cycle's :class:`~fourseer.models.CycleMetrics`.

    ``mode`` is derived from ``metrics.outcome`` via the total mapping in the
    module docstring. When *gate_log* is supplied, the matching
    :class:`~fourseer.models.CycleBlock` (by ``cycle_no``) is looked up and its
    ``gate_after`` / ``merged`` fields copied into the classification; when no
    block matches (or the block has no ``### Results`` table) both stay ``None``.
    ``gate`` / ``merged`` are best-effort enrichment and never affect ``mode``.

    The function is pure and deterministic: it does no I/O and never mutates
    *metrics* or *gate_log*.
    """
    mode = _mode_from_outcome(metrics.outcome)
    gate: str | None = None
    merged: bool | None = None
    if gate_log is not None:
        for block in gate_log.cycles:
            if block.cycle_no == metrics.cycle_no:
                gate = block.gate_after
                merged = block.merged
                break
    return CycleClassification(
        cycle_no=metrics.cycle_no,
        mode=mode,
        gate=gate,
        merged=merged,
    )


def classify_run(run: Run) -> list[CycleClassification]:
    """Classify every executed cycle in *run*, sorted by ``cycle_no``.

    Builds :func:`~fourseer.report.build_cycle_metrics` for *run* and classifies
    each metric with *run*'s gate log. Only the cycles present in
    ``cycles.out`` (the ``build_cycle_metrics`` output) are classified; cycles
    that appear only in the gate log are ignored, and a cycle with no matching
    gate-log block simply has ``gate`` / ``merged`` left ``None``.

    The function is pure and deterministic: it does no I/O and never mutates
    *run*.
    """
    metrics = build_cycle_metrics(run)
    return [classify_cycle(m, run.gate_log) for m in metrics]
