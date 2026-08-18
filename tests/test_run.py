"""Tests for the :class:`fourseer.models.Run` aggregate dataclass.

Covers field defaults (empty lists / empty GateLog), frozen-ness, the
``trajectory_count`` / ``cycle_count`` properties, and the ``killed_cycles()``
helper (TICKET-006).
"""

from __future__ import annotations

import dataclasses

import pytest

from fourseer.models import (
    CommitRecord,
    CycleRecord,
    GateLog,
    Run,
    Trajectory,
)


def test_run_defaults() -> None:
    """A bare Run has empty trajectories/cycles/commits and an empty GateLog."""
    r = Run()
    assert r.trajectories == []
    assert r.cycles == []
    assert r.commits == []
    assert isinstance(r.gate_log, GateLog)
    assert r.gate_log.build_order == []
    assert r.gate_log.cycles == []


def test_run_defaults_are_independent() -> None:
    """List defaults are per-instance (default_factory), not shared."""
    a = Run()
    b = Run()
    a.trajectories.append(Trajectory(outcome="x"))
    assert b.trajectories == []

    c = Run()
    d = Run()
    c.cycles.append(CycleRecord(cycle_no=1, timestamp="t"))
    assert d.cycles == []


def test_run_is_frozen() -> None:
    """Run is a frozen dataclass: mutation raises FrozenInstanceError."""
    r = Run()
    assert dataclasses.is_dataclass(r)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.trajectories = []


def test_trajectory_count_property() -> None:
    r = Run(trajectories=[Trajectory(outcome="a"), Trajectory(outcome="b")])
    assert r.trajectory_count == 2
    assert Run().trajectory_count == 0


def test_cycle_count_property() -> None:
    r = Run(cycles=[CycleRecord(cycle_no=1, timestamp="t"),
                    CycleRecord(cycle_no=2, timestamp="t")])
    assert r.cycle_count == 2
    assert Run().cycle_count == 0


def test_killed_cycles_returns_none_outcome_numbers() -> None:
    """killed_cycles() returns cycle_no where outcome is None, in file order."""
    r = Run(
        cycles=[
            CycleRecord(cycle_no=7, timestamp="t", outcome="max_steps_reached"),
            CycleRecord(cycle_no=21, timestamp="t", outcome=None),
            CycleRecord(cycle_no=22, timestamp="t", outcome=None),
            CycleRecord(cycle_no=25, timestamp="t", outcome=None),
        ]
    )
    assert r.killed_cycles() == [21, 22, 25]


def test_killed_cycles_empty_when_all_completed() -> None:
    r = Run(cycles=[CycleRecord(cycle_no=1, timestamp="t", outcome="exit:task_complete")])
    assert r.killed_cycles() == []
    assert Run().killed_cycles() == []


def test_run_holds_all_four_artifacts() -> None:
    """A fully-populated Run carries all four parser outputs."""
    r = Run(
        trajectories=[Trajectory(outcome="x")],
        cycles=[CycleRecord(cycle_no=1, timestamp="t")],
        gate_log=GateLog(),
        commits=[CommitRecord(hash="h", short_hash="s", author="a", date="d", subject="s")],
    )
    assert r.trajectory_count == 1
    assert r.cycle_count == 1
    assert len(r.commits) == 1
    assert r.commits[0].subject == "s"
