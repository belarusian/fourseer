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

:func:`summarize_taxonomy` rolls a run's per-cycle classifications up into a
single :class:`~fourseer.models.TaxonomySummary` (the run-level failure-mode
distribution), and :func:`render_taxonomy` renders that aggregate as a short,
deterministic human-readable block. Both are pure, deterministic, stdlib-only,
and perform no I/O.
"""

from __future__ import annotations

from fourseer.models import (
    CycleClassification,
    CycleMetrics,
    GateLog,
    Run,
    TaxonomySummary,
)
from fourseer.report import build_cycle_metrics

__all__ = ["classify_cycle", "classify_run", "render_taxonomy", "summarize_taxonomy"]

# The closed, stable set of failure-mode tags (documented in the module
# docstring and on :class:`CycleClassification`).
MODE_WALL_CLOCK_KILL = "wall_clock_kill"
MODE_MAX_STEPS = "max_steps"
MODE_TASK_COMPLETE = "task_complete"
MODE_EXECUTION_ERROR = "execution_error"
MODE_FORMAT_ERROR = "format_error"
MODE_OTHER = "other"

# The single stable placeholder for an empty distribution in the rendered block.
_PLACEHOLDER = "-"


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


def summarize_taxonomy(
    classifications: list[CycleClassification],
) -> TaxonomySummary:
    """Roll a run's per-cycle :class:`~fourseer.models.CycleClassification`
    list up into a single :class:`~fourseer.models.TaxonomySummary`.

    A pure, deterministic, stdlib-only aggregation. It performs no I/O and
    never mutates *classifications*.

    The three distributions are built by counting:

    - ``mode_counts`` — every classification contributes its ``mode`` (a total
      mapping, so every cycle is counted);
    - ``gate_counts`` — only classifications whose ``gate`` is non-``None``
      contribute their gate tag; the rest are tallied in ``gate_unknown``;
    - ``merged_counts`` — only classifications whose ``merged`` is non-``None``
      contribute their merge flag (keyed ``"merged"`` when ``True`` and
      ``"not_merged"`` when ``False``); the rest are tallied in
      ``merged_unknown``.

    Only tags / flags that actually occur appear as keys, so an empty or
    single-mode run yields a sparse mapping.

    Parameters
    ----------
    classifications:
        The per-cycle classifications to aggregate (typically the output of
        :func:`classify_run`). Never mutated.

    Returns
    -------
    TaxonomySummary
        The run-level failure-mode distribution.
    """
    cycle_count = len(classifications)

    mode_counts: dict[str, int] = {}
    gate_counts: dict[str, int] = {}
    merged_counts: dict[str, int] = {}
    gate_unknown = 0
    merged_unknown = 0

    for c in classifications:
        mode_counts[c.mode] = mode_counts.get(c.mode, 0) + 1
        if c.gate is None:
            gate_unknown += 1
        else:
            gate_counts[c.gate] = gate_counts.get(c.gate, 0) + 1
        if c.merged is None:
            merged_unknown += 1
        else:
            key = "merged" if c.merged else "not_merged"
            merged_counts[key] = merged_counts.get(key, 0) + 1

    return TaxonomySummary(
        cycle_count=cycle_count,
        mode_counts=mode_counts,
        gate_counts=gate_counts,
        gate_unknown=gate_unknown,
        merged_counts=merged_counts,
        merged_unknown=merged_unknown,
    )


def render_taxonomy(summary: TaxonomySummary) -> str:
    """Render a :class:`~fourseer.models.TaxonomySummary` as a short block.

    A pure, deterministic, stdlib-only string transformation, consistent in
    style with :func:`fourseer.report.render_summary`:

    - a header line ``# Failure-Mode Taxonomy (N cycles)`` where ``N`` is
      ``summary.cycle_count``;
    - a ``cycles:`` line;
    - a ``modes:`` line listing each mode tag and its count, sorted by tag
      (deterministic), or ``-`` when there are no cycles;
    - a ``gates:`` line listing each gate tag and its count, sorted by tag,
      followed by ``unknown: <n>`` when ``gate_unknown`` is non-zero, or ``-``
      when there are no cycles;
    - a ``merged:`` line listing each merge flag and its count, sorted by flag,
      followed by ``unknown: <n>`` when ``merged_unknown`` is non-zero, or
      ``-`` when there are no cycles.

    Parameters
    ----------
    summary:
        The run-level failure-mode distribution to render. Never mutated.

    Returns
    -------
    str
        The rendered taxonomy block, ending with a trailing newline.
    """
    lines: list[str] = [
        f"# Failure-Mode Taxonomy ({summary.cycle_count} cycles)",
        "",
        f"cycles: {summary.cycle_count}",
    ]

    if summary.mode_counts:
        modes = ", ".join(
            f"{tag}={summary.mode_counts[tag]}" for tag in sorted(summary.mode_counts)
        )
    else:
        modes = _PLACEHOLDER
    lines.append(f"modes: {modes}")

    if summary.gate_counts:
        gates = ", ".join(
            f"{tag}={summary.gate_counts[tag]}" for tag in sorted(summary.gate_counts)
        )
        if summary.gate_unknown:
            gates += f", unknown={summary.gate_unknown}"
    else:
        gates = _PLACEHOLDER
    lines.append(f"gates: {gates}")

    if summary.merged_counts:
        merged = ", ".join(
            f"{flag}={summary.merged_counts[flag]}" for flag in sorted(summary.merged_counts)
        )
        if summary.merged_unknown:
            merged += f", unknown={summary.merged_unknown}"
    else:
        merged = _PLACEHOLDER
    lines.append(f"merged: {merged}")

    return "\n".join(lines) + "\n"
