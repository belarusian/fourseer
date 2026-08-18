"""Typed data models for fourseer's parsed artifacts.

These are the canonical, stdlib-only dataclasses that every parser in
``fourseer.parse`` produces and every consumer (report / taxonomy / drift)
consumes. They are pure value objects: no I/O, no side effects, no
dependencies beyond the standard library.

Models
------
- :class:`Trajectory`      — one inner-loop run (a ``trajectories/*.json`` file).
- :class:`CycleRecord`     — one outer-loop cycle header from ``cycles.out``.
- :class:`BuildOrderRow`   — one row of the gate-log "Build Order" table.
- :class:`CycleBlock`      — one "## Cycle N" block from the gate log.
- :class:`GateLog`         — the whole gate log: build order + cycle blocks.
- :class:`CommitRecord`    — one commit from ``git log``.
- :class:`ConsistencyIssue`— one cross-source inconsistency (validator output).
- :class:`CycleMetrics`    — per-cycle metrics (report output).
- :class:`RunSummary`      — run-level totals aggregated from per-cycle metrics.
- :class:`CycleClassification` — one cycle's failure-mode classification (taxonomy output).

Field semantics are documented per-field. Where a source artifact may omit a
value (e.g. a wall-clock-killed cycle that never wrote an ``OUTER`` line), the
corresponding field is typed ``Optional`` and defaults to ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Trajectory:
    """A single inner-loop trajectory (one ``trajectories/trajectory_NNNN.json``).

    The on-disk JSON carries at least ``outcome`` and ``messages``. ``step_count``
    is NOT always present in the file; when absent it is derived as the number of
    messages (see :func:`fourseer.parse.trajectories.load_trajectories`).

    Attributes
    ----------
    outcome:
        The run's terminal outcome string, e.g. ``"exit:task_complete"`` or
        ``"max_steps_reached"``. May be ``None`` if the file omits it.
    messages:
        The ordered list of message dicts (each with ``role`` / ``content``).
        Tolerant of extra per-message keys.
    step_count:
        Number of steps. Derived from ``len(messages)`` when the file has no
        explicit ``step_count`` key.
    name:
        The source filename (basename, e.g. ``"trajectory_0013.json"``) the
        trajectory was loaded from, or ``""`` when constructed directly.
        Populated by :func:`fourseer.parse.trajectories.load_trajectories` so
        consumers can correlate a cycle's referenced trajectory path with the
        set of loaded trajectories.
    """

    outcome: str | None
    messages: list[dict[str, Any]] = field(default_factory=list)
    step_count: int = 0
    name: str = ""


@dataclass(frozen=True)
class ConsistencyIssue:
    """One cross-source inconsistency found by :func:`fourseer.validate.validate_run`.

    A pure, hashable, comparable value object describing a single mismatch
    between the four independently-parsed sources in a :class:`Run`. The
    validator returns a deterministic, sorted list of these.

    Attributes
    ----------
    code:
        A stable machine tag (snake_case) identifying the check that fired.
        Canonical values:

        - ``"orphan_trajectory_path"`` — a ``CycleRecord.trajectory_path``
          basename that is not among the loaded ``Trajectory.name`` values.
        - ``"cycle_not_in_gate_log"`` — a ``CycleRecord.cycle_no`` with no
          matching ``CycleBlock.cycle_no`` in the gate log.
        - ``"gate_cycle_not_in_cycles_out"`` — a ``CycleBlock.cycle_no`` with
          no matching ``CycleRecord.cycle_no`` in ``cycles.out``.
        - ``"build_order_range_gap"`` — an executed ``CycleRecord.cycle_no``
          outside every Build Order range.
    cycle_no:
        The cycle the issue concerns, or ``None`` when the issue is not tied to
        a single cycle.
    detail:
        A free-text, deterministic human-readable explanation.
    """

    code: str
    cycle_no: int | None
    detail: str


@dataclass(frozen=True)
class CycleRecord:
    """One outer-loop cycle as recorded in ``cycles.out``.

    A cycle header line looks like ``========== CYCLE 7  16:30:45Z ==========``.
    The fourseer runner prefixes the header with a project name
    (``========== FOURSEER CYCLE 1  13:48:31Z ==========``); both forms parse.

    A cycle that is killed by the wall-clock alarm writes NO ``OUTER`` lines, so
    ``outcome`` and ``trajectory_path`` are ``None`` for such cycles.

    Attributes
    ----------
    cycle_no:
        The integer cycle number from the header.
    timestamp:
        The wall-clock time string from the header, e.g. ``"16:30:45Z"``.
    outcome:
        The ``OUTER outcome:`` value, or ``None`` if the cycle was killed before
        writing one.
    trajectory_path:
        The ``OUTER trajectory saved to:`` path, or ``None`` if absent.
    """

    cycle_no: int
    timestamp: str
    outcome: str | None = None
    trajectory_path: str | None = None


@dataclass(frozen=True)
class BuildOrderRow:
    """One row of the gate-log "## Build Order" markdown table.

    Attributes
    ----------
    phase:
        The phase name, e.g. ``"Foundations"``.
    cycles:
        The cycle-range string, e.g. ``"1-3"`` (kept as a string; ranges are
        parsed by consumers, not here).
    target:
        The free-text target description for the phase.
    """

    phase: str
    cycles: str
    target: str


@dataclass(frozen=True)
class CycleBlock:
    """One "## Cycle N" block from the gate log.

    The block header is ``## Cycle N: <title>`` (the title may be absent, e.g.
    ``## Cycle 1 — Pending``). The body carries optional ``**Date:**``,
    ``**HEAD (start):**`` and ``**HEAD (end):**`` fields and an optional
    ``### Lessons`` section.

    Attributes
    ----------
    cycle_no:
        The integer cycle number from the header.
    title:
        The free-text title after the colon, or ``""`` if none.
    date:
        The ``**Date:**`` value, or ``None``.
    head_start:
        The ``**HEAD (start):**`` value, or ``None``.
    head_end:
        The ``**HEAD (end):**`` value, or ``None``.
    lessons:
        The list of lesson strings from the ``### Lessons`` section (numbered
        items, leading markers stripped), or an empty list.
    gate_after:
        The ``### Results`` table's ``Gate (build+test+lint)`` row ``After``
        cell, lowercased to ``"green"`` / ``"red"``, or ``None`` when the block
        has no ``### Results`` table (or the row is absent).
    merged:
        Whether the cycle was merged on main, read from the ``### Results``
        table's ``Merged on main`` row ``After`` cell: ``True`` when the cell
        carries a commit hash / PR reference, ``False`` when it is an em-dash
        or empty, and ``None`` when the block has no ``### Results`` table (or
        the row is absent).
    """

    cycle_no: int
    title: str = ""
    date: str | None = None
    head_start: str | None = None
    head_end: str | None = None
    lessons: list[str] = field(default_factory=list)
    gate_after: str | None = None
    merged: bool | None = None


@dataclass(frozen=True)
class GateLog:
    """The parsed gate log: the Build Order plan plus every cycle block.

    Attributes
    ----------
    build_order:
        The rows of the "## Build Order" table, in file order.
    cycles:
        The "## Cycle N" blocks, in file order.
    """

    build_order: list[BuildOrderRow] = field(default_factory=list)
    cycles: list[CycleBlock] = field(default_factory=list)


@dataclass(frozen=True)
class CommitRecord:
    """One commit from ``git log``.

    Attributes
    ----------
    hash:
        The full 40-char commit hash.
    short_hash:
        The abbreviated hash (``%h``).
    author:
        The author name (``%an``).
    date:
        The author date in ISO form (``%ad`` with ``--date=iso``).
    subject:
        The commit subject line (``%s``).
    """

    hash: str
    short_hash: str
    author: str
    date: str
    subject: str


@dataclass(frozen=True)
class Run:
    """A complete run of the outer loop: the four parsed artifacts together.

    This is the top-level aggregate that composes the outputs of the four
    parsers in :mod:`fourseer.parse` into a single value object a consumer
    (report / taxonomy / drift) can hold:

    - :func:`~fourseer.parse.trajectories.load_trajectories` -> ``trajectories``
    - :func:`~fourseer.parse.cycles_out.parse_cycles_out`     -> ``cycles``
    - :func:`~fourseer.parse.gate_log.parse_gate_log`         -> ``gate_log``
    - :func:`~fourseer.parse.git_history.read_git_history`    -> ``commits``

    All fields default to empty so a ``Run`` can be built incrementally or
    from a partial artifact set (see :func:`fourseer.load.load_run`, which
    tolerates missing optional files).

    Attributes
    ----------
    trajectories:
        The inner-loop trajectories (one per ``trajectories/*.json``).
    cycles:
        The outer-loop cycle records from ``cycles.out``.
    gate_log:
        The parsed gate log (Build Order table + cycle blocks).
    commits:
        The git commit history (empty when no repo was supplied).
    """

    trajectories: list[Trajectory] = field(default_factory=list)
    cycles: list[CycleRecord] = field(default_factory=list)
    gate_log: GateLog = field(default_factory=GateLog)
    commits: list[CommitRecord] = field(default_factory=list)

    @property
    def trajectory_count(self) -> int:
        """Number of trajectories in this run."""
        return len(self.trajectories)

    @property
    def cycle_count(self) -> int:
        """Number of cycle records in this run."""
        return len(self.cycles)

    def killed_cycles(self) -> list[int]:
        """Cycle numbers that were killed before writing an ``OUTER`` outcome.

        A wall-clock-killed cycle has ``outcome is None`` (see
        :class:`CycleRecord`). Returns the matching ``cycle_no`` values in
        file order.
        """
        return [c.cycle_no for c in self.cycles if c.outcome is None]


@dataclass(frozen=True)
class CycleMetrics:
    """Per-cycle metrics for one outer-loop cycle (a pure value object).

    Produced by :func:`fourseer.report.build_cycle_metrics`. It joins a
    :class:`CycleRecord` with the :class:`Trajectory` it references (by
    trajectory basename) and derives the wall-clock duration of the cycle from
    the gap between this cycle's start timestamp and the next cycle's start
    timestamp (with a midnight wrap).

    Attributes
    ----------
    cycle_no:
        The integer cycle number (from the ``CycleRecord``).
    outcome:
        The ``CycleRecord.outcome`` value, or ``None`` for a wall-clock-killed
        cycle that never wrote an ``OUTER`` line.
    step_count:
        The joined trajectory's ``step_count``, or ``0`` when no trajectory is
        joined (a kill, or an orphaned path).
    duration_seconds:
        Wall-clock seconds between this cycle's start and the next cycle's
        start (midnight-wrapped), or ``None`` for the last cycle in file order
        (no following start) or when not computable.
    trajectory_name:
        The joined ``Trajectory.name`` (source basename), or ``None`` when no
        trajectory is joined.
    """

    cycle_no: int
    outcome: str | None
    step_count: int
    duration_seconds: int | None
    trajectory_name: str | None

@dataclass(frozen=True)
class RunSummary:
    """Run-level totals aggregated from a run's per-cycle :class:`CycleMetrics`.

    A pure, hashable, comparable value object that rolls a whole run's
    per-cycle metrics up into a single aggregate a consumer (CLI, taxonomy,
    drift) can hold. Produced by :func:`fourseer.report.summarize_run`.

    Invariant
    ---------
    ``completed_count + killed_count == cycle_count``: every cycle either
    wrote an ``OUTER`` outcome (completed) or was wall-clock-killed before
    writing one (killed), so the two counts partition the total.

    Attributes
    ----------
    cycle_count:
        The total number of cycles (``len(metrics)``).
    completed_count:
        The number of cycles with a non-``None`` ``outcome`` (a completed run).
    killed_count:
        The number of cycles with ``outcome is None`` (a wall-clock kill).
    total_steps:
        The sum of every cycle's ``step_count`` (``0`` when there are no
        cycles).
    total_duration_seconds:
        The sum of the non-``None`` ``duration_seconds`` values (``0`` when no
        cycle carries a duration, e.g. a single-cycle run).
    cycles_with_duration:
        The number of cycles whose ``duration_seconds`` is non-``None``.
    total_tokens:
        The summed token count across the DISTINCT trajectories the run's
        cycles reference, or ``None`` when no referenced trajectory carries a
        usage record (or when no trajectories were supplied).
    total_cost:
        The summed cost across the DISTINCT trajectories the run's cycles
        reference, or ``None`` when no referenced trajectory carries a usage
        record (or when no trajectories were supplied).
    """

    cycle_count: int
    completed_count: int
    killed_count: int
    total_steps: int
    total_duration_seconds: int
    cycles_with_duration: int
    total_tokens: int | None
    total_cost: float | None


@dataclass(frozen=True)
class CycleClassification:
    """One cycle's failure-mode classification (a pure value object).

    Produced by :func:`fourseer.taxonomy.classify_cycle`. It tags a single
    outer-loop cycle with a stable failure-mode ``mode`` and, when the gate log
    carries a matching ``### Results`` table, the cycle's gate outcome and
    merge status.

    The closed set of ``mode`` values is:

    - ``"wall_clock_kill"``   — the cycle was killed by the wall-clock alarm
      before writing an ``OUTER`` outcome (``metrics.outcome is None``).
    - ``"max_steps"``         — the inner loop ran to its step budget
      (``metrics.outcome == "max_steps_reached"``).
    - ``"task_complete"``     — the inner loop completed the task
      (``metrics.outcome == "exit:task_complete"``).
    - ``"execution_error"``   — the inner loop died on an execution error
      (``metrics.outcome`` starts with ``"execution_error"``).
    - ``"format_error"``      — the inner loop died on a repeated format error
      (``metrics.outcome`` starts with ``"repeated_format_error"``).
    - ``"other"``             — any other non-``None`` outcome.

    Attributes
    ----------
    cycle_no:
        The integer cycle number (from the :class:`CycleMetrics`).
    mode:
        The failure-mode tag, one of the six values above.
    gate:
        The matching :class:`CycleBlock`'s ``gate_after`` (``"green"`` /
        ``"red"``), or ``None`` when the gate log has no matching block or the
        block has no ``### Results`` table.
    merged:
        The matching :class:`CycleBlock`'s ``merged`` (``True`` / ``False``),
        or ``None`` when the gate log has no matching block or the block has no
        ``### Results`` table.
    """

    cycle_no: int
    mode: str
    gate: str | None = None
    merged: bool | None = None
