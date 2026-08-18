"""Tests for the typed data models in :mod:`fourseer.models`.

Verifies field defaults, frozen-ness (mutation raises), and the list defaults
on :class:`GateLog` / :class:`CycleBlock` (TICKET-001).
"""

from __future__ import annotations

import dataclasses

import pytest

from fourseer.models import (
    BuildOrderRow,
    CommitRecord,
    ConsistencyIssue,
    CycleBlock,
    CycleMetrics,
    CycleRecord,
    GateLog,
    Trajectory,
)


def test_trajectory_defaults() -> None:
    t = Trajectory(outcome="exit:task_complete")
    assert t.outcome == "exit:task_complete"
    assert t.messages == []
    assert t.step_count == 0


def test_trajectory_none_outcome() -> None:
    t = Trajectory(outcome=None, messages=[{"role": "user", "content": "hi"}])
    assert t.outcome is None
    assert t.step_count == 0
    assert t.messages == [{"role": "user", "content": "hi"}]


def test_cycle_record_defaults() -> None:
    r = CycleRecord(cycle_no=7, timestamp="16:30:45Z")
    assert r.cycle_no == 7
    assert r.timestamp == "16:30:45Z"
    assert r.outcome is None
    assert r.trajectory_path is None


def test_build_order_row() -> None:
    row = BuildOrderRow(phase="Foundations", cycles="1-3", target="Session log")
    assert row.phase == "Foundations"
    assert row.cycles == "1-3"
    assert row.target == "Session log"


def test_cycle_block_defaults() -> None:
    b = CycleBlock(cycle_no=1)
    assert b.cycle_no == 1
    assert b.title == ""
    assert b.date is None
    assert b.head_start is None
    assert b.head_end is None
    assert b.lessons == []


def test_gate_log_list_defaults() -> None:
    gl = GateLog()
    assert gl.build_order == []
    assert gl.cycles == []


def test_commit_record() -> None:
    c = CommitRecord(
        hash="a" * 40, short_hash="a" * 7, author="sasha", date="2026-08-17 10:00:00", subject="init"
    )
    assert c.hash == "a" * 40
    assert c.short_hash == "a" * 7
    assert c.author == "sasha"
    assert c.date == "2026-08-17 10:00:00"
    assert c.subject == "init"


def test_all_models_are_frozen() -> None:
    """Every model is a frozen dataclass: mutation raises FrozenInstanceError."""
    samples = [
        Trajectory(outcome="x"),
        CycleRecord(cycle_no=1, timestamp="t"),
        BuildOrderRow(phase="p", cycles="c", target="t"),
        CycleBlock(cycle_no=1),
        GateLog(),
        CommitRecord(hash="h", short_hash="s", author="a", date="d", subject="s"),
    ]
    for obj in samples:
        assert dataclasses.is_dataclass(obj)
        first = dataclasses.fields(obj)[0].name
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, first, "boom")


def test_gate_log_and_cycle_block_have_independent_list_defaults() -> None:
    """List defaults are per-instance (default_factory), not shared."""
    a = GateLog()
    b = GateLog()
    a.build_order.append(BuildOrderRow(phase="p", cycles="c", target="t"))
    assert b.build_order == []

    c = CycleBlock(cycle_no=1)
    d = CycleBlock(cycle_no=2)
    c.lessons.append("lesson")
    assert d.lessons == []


def test_trajectory_name_defaults_empty() -> None:
    """Trajectory.name defaults to '' (backward compatible trailing field)."""
    t = Trajectory(outcome="exit:task_complete")
    assert t.name == ""


def test_trajectory_name_explicit() -> None:
    """Trajectory.name can be set explicitly (e.g. the source basename)."""
    t = Trajectory(outcome="x", name="trajectory_0013.json")
    assert t.name == "trajectory_0013.json"


def test_consistency_issue_fields() -> None:
    """ConsistencyIssue carries code / cycle_no / detail."""
    i = ConsistencyIssue(code="orphan_trajectory_path", cycle_no=7, detail="no such file")
    assert i.code == "orphan_trajectory_path"
    assert i.cycle_no == 7
    assert i.detail == "no such file"


def test_consistency_issue_none_cycle_no() -> None:
    """cycle_no may be None when the issue is not tied to a single cycle."""
    i = ConsistencyIssue(code="build_order_range_gap", cycle_no=None, detail="d")
    assert i.cycle_no is None


def test_consistency_issue_is_frozen() -> None:
    """ConsistencyIssue is a frozen dataclass: mutation raises."""
    i = ConsistencyIssue(code="c", cycle_no=1, detail="d")
    assert dataclasses.is_dataclass(i)
    with pytest.raises(dataclasses.FrozenInstanceError):
        i.code = "boom"


def test_consistency_issue_hashable_and_equal() -> None:
    """Two identical ConsistencyIssue instances compare equal and hash equal."""
    a = ConsistencyIssue(code="c", cycle_no=1, detail="d")
    b = ConsistencyIssue(code="c", cycle_no=1, detail="d")
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_cycle_metrics_fields() -> None:
    """CycleMetrics carries all five fields with the given values."""
    m = CycleMetrics(
        cycle_no=7,
        outcome="max_steps_reached",
        step_count=82,
        duration_seconds=3505,
        trajectory_name="trajectory_0013.json",
    )
    assert m.cycle_no == 7
    assert m.outcome == "max_steps_reached"
    assert m.step_count == 82
    assert m.duration_seconds == 3505
    assert m.trajectory_name == "trajectory_0013.json"


def test_cycle_metrics_kill_shape() -> None:
    """A wall-clock kill: outcome None, step_count 0, trajectory_name None."""
    m = CycleMetrics(
        cycle_no=21,
        outcome=None,
        step_count=0,
        duration_seconds=3600,
        trajectory_name=None,
    )
    assert m.outcome is None
    assert m.step_count == 0
    assert m.trajectory_name is None


def test_cycle_metrics_last_cycle_duration_none() -> None:
    """The last cycle has duration_seconds None (no following start)."""
    m = CycleMetrics(
        cycle_no=28,
        outcome="exit:task_complete",
        step_count=39,
        duration_seconds=None,
        trajectory_name="trajectory_0043.json",
    )
    assert m.duration_seconds is None


def test_cycle_metrics_is_frozen() -> None:
    """CycleMetrics is a frozen dataclass: mutation raises."""
    m = CycleMetrics(1, "x", 2, 3, "t")
    assert dataclasses.is_dataclass(m)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.cycle_no = 99


def test_cycle_metrics_hashable_and_equal() -> None:
    """Two identical CycleMetrics compare equal and hash equal."""
    a = CycleMetrics(7, "max_steps_reached", 82, 3505, "trajectory_0013.json")
    b = CycleMetrics(7, "max_steps_reached", 82, 3505, "trajectory_0013.json")
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1
