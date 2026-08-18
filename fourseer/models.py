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
    """

    cycle_no: int
    title: str = ""
    date: str | None = None
    head_start: str | None = None
    head_end: str | None = None
    lessons: list[str] = field(default_factory=list)


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
