"""Focused unit tests for :func:`fourseer.validate.validate_run`.

Uses small INLINE hand-built :class:`Run` fixtures (not the seed) to localize
each cross-check, plus exactly ONE real-seed test that pins the validator's
behavior on the actual dataset (TICKET-012 / TICKET-013).
"""

from __future__ import annotations

from fourseer.load import load_run
from fourseer.models import (
    BuildOrderRow,
    CycleBlock,
    CycleRecord,
    GateLog,
    Run,
    Trajectory,
)
from fourseer.validate import validate_run


def _snapshot(run: Run) -> tuple:
    """A deep-ish, comparable snapshot of the parts of *run* a validator might
    (incorrectly) mutate."""
    return (
        [(c.cycle_no, c.timestamp, c.outcome, c.trajectory_path) for c in run.cycles],
        [(b.cycle_no, b.title) for b in run.gate_log.cycles],
        [(r.phase, r.cycles, r.target) for r in run.gate_log.build_order],
        [(t.name, t.outcome, t.step_count) for t in run.trajectories],
        len(run.commits),
    )


def _consistent_run() -> Run:
    """A fully internally-consistent run: every cross-check passes."""
    return Run(
        trajectories=[
            Trajectory(outcome="x", name="trajectory_0001.json"),
            Trajectory(outcome="x", name="trajectory_0002.json"),
        ],
        cycles=[
            CycleRecord(cycle_no=1, timestamp="t", trajectory_path="/x/trajectory_0001.json"),
            CycleRecord(cycle_no=2, timestamp="t", trajectory_path="/x/trajectory_0002.json"),
        ],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="1-2", target="t")],
            cycles=[CycleBlock(cycle_no=1), CycleBlock(cycle_no=2)],
        ),
    )


def test_consistent_run_returns_empty() -> None:
    """A run where every cross-check passes yields []."""
    assert validate_run(_consistent_run()) == []


def test_orphan_trajectory_path() -> None:
    """(a) a referenced trajectory basename not among loaded names -> one orphan."""
    run = Run(
        trajectories=[Trajectory(outcome="x", name="trajectory_0001.json")],
        cycles=[CycleRecord(cycle_no=1, timestamp="t", trajectory_path="/x/trajectory_9999.json")],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="1-2", target="t")],
            cycles=[CycleBlock(cycle_no=1)],
        ),
    )
    issues = validate_run(run)
    assert len(issues) == 1
    assert issues[0].code == "orphan_trajectory_path"
    assert issues[0].cycle_no == 1


def test_trajectory_path_matching_emits_no_orphan() -> None:
    """(a) a full path whose basename matches a loaded name emits no orphan."""
    run = Run(
        trajectories=[Trajectory(outcome="x", name="trajectory_0007.json")],
        cycles=[CycleRecord(cycle_no=7, timestamp="t", trajectory_path="/deep/path/trajectory_0007.json")],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="7", target="t")],
            cycles=[CycleBlock(cycle_no=7)],
        ),
    )
    assert validate_run(run) == []


def test_cycle_not_in_gate_log() -> None:
    """(b) a cycle record with no matching gate block -> cycle_not_in_gate_log."""
    run = Run(
        trajectories=[],
        cycles=[
            CycleRecord(cycle_no=1, timestamp="t"),
            CycleRecord(cycle_no=2, timestamp="t"),
        ],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="1-2", target="t")],
            cycles=[CycleBlock(cycle_no=1)],
        ),
    )
    issues = validate_run(run)
    assert len(issues) == 1
    assert issues[0].code == "cycle_not_in_gate_log"
    assert issues[0].cycle_no == 2


def test_gate_cycle_not_in_cycles_out() -> None:
    """(b') a gate block with no matching cycle record -> gate_cycle_not_in_cycles_out."""
    run = Run(
        trajectories=[],
        cycles=[CycleRecord(cycle_no=1, timestamp="t")],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="1-2", target="t")],
            cycles=[CycleBlock(cycle_no=1), CycleBlock(cycle_no=2)],
        ),
    )
    issues = validate_run(run)
    assert len(issues) == 1
    assert issues[0].code == "gate_cycle_not_in_cycles_out"
    assert issues[0].cycle_no == 2


def test_build_order_range_gap() -> None:
    """(c) an executed cycle outside every Build Order range -> build_order_range_gap."""
    run = Run(
        trajectories=[],
        cycles=[
            CycleRecord(cycle_no=1, timestamp="t"),
            CycleRecord(cycle_no=5, timestamp="t"),
        ],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="1-3", target="t")],
            cycles=[CycleBlock(cycle_no=1), CycleBlock(cycle_no=5)],
        ),
    )
    issues = validate_run(run)
    assert len(issues) == 1
    assert issues[0].code == "build_order_range_gap"
    assert issues[0].cycle_no == 5


def test_determinism_and_sorted_order() -> None:
    """Calling twice yields equal lists; the list is sorted by the stable key."""
    run = Run(
        trajectories=[Trajectory(outcome="x", name="trajectory_0001.json")],
        cycles=[
            CycleRecord(cycle_no=1, timestamp="t", trajectory_path="/x/trajectory_9999.json"),
            CycleRecord(cycle_no=2, timestamp="t"),
            CycleRecord(cycle_no=9, timestamp="t"),
        ],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="1-3", target="t")],
            cycles=[CycleBlock(cycle_no=1), CycleBlock(cycle_no=4)],
        ),
    )
    issues = validate_run(run)
    # Determinism: identical result on a second call.
    assert issues == validate_run(run)
    # Sorted by the stable key (code, cycle_no or -1, detail).
    keys = [(i.code, i.cycle_no if i.cycle_no is not None else -1, i.detail) for i in issues]
    assert keys == sorted(keys)
    # The exact (code, cycle_no) sequence in sorted order.
    assert [(i.code, i.cycle_no) for i in issues] == [
        ("build_order_range_gap", 9),
        ("cycle_not_in_gate_log", 2),
        ("cycle_not_in_gate_log", 9),
        ("gate_cycle_not_in_cycles_out", 4),
        ("orphan_trajectory_path", 1),
    ]


def test_no_mutation() -> None:
    """validate_run never mutates its input Run."""
    run = Run(
        trajectories=[Trajectory(outcome="x", name="trajectory_0001.json")],
        cycles=[
            CycleRecord(cycle_no=1, timestamp="t", trajectory_path="/x/trajectory_9999.json"),
            CycleRecord(cycle_no=2, timestamp="t"),
        ],
        gate_log=GateLog(
            build_order=[BuildOrderRow(phase="P", cycles="1-2", target="t")],
            cycles=[CycleBlock(cycle_no=1), CycleBlock(cycle_no=3)],
        ),
    )
    before = _snapshot(run)
    validate_run(run)
    assert _snapshot(run) == before


def test_seed_validate(seed_dir) -> None:
    """Exactly ONE real-seed test: pin the validator's behavior on the dataset."""
    run = load_run(seed_dir)
    issues = validate_run(run)
    codes = {i.code for i in issues}
    assert codes == {
        "cycle_not_in_gate_log",
        "gate_cycle_not_in_cycles_out",
        "build_order_range_gap",
    }
    assert {i.cycle_no for i in issues if i.code == "cycle_not_in_gate_log"} == {21, 22}
    assert {i.cycle_no for i in issues if i.code == "gate_cycle_not_in_cycles_out"} == {1, 2, 3, 4, 5, 6}
    assert {i.cycle_no for i in issues if i.code == "build_order_range_gap"} == {
        21, 22, 23, 24, 25, 26, 27, 28,
    }
    assert not any(i.code == "orphan_trajectory_path" for i in issues)
