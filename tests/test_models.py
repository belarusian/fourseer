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
    CycleBlock,
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
