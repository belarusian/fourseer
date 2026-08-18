"""Tests for :func:`fourseer.report.build_cycle_metrics`.

Most tests use small hand-built :class:`~fourseer.models.Run` fixtures (not the
full seed) to isolate each behavior: basename join, kill no-join, start-to-next
duration, midnight wrap, last-cycle ``None`` duration, ``cycle_no`` ordering,
and no-mutation / determinism. Exactly one test exercises the real seed dataset
via the ``seed_dir`` fixture.
"""

from __future__ import annotations

import copy

from fourseer.load import load_run
from fourseer.models import CycleMetrics, CycleRecord, Run, Trajectory
from fourseer.report import build_cycle_metrics


def _metrics_by_cycle(run: Run) -> dict[int, CycleMetrics]:
    return {m.cycle_no: m for m in build_cycle_metrics(run)}


def _sample_run() -> Run:
    """A small run: two joined cycles, one kill, one last cycle (midnight wrap)."""
    trajectories = [
        Trajectory(outcome="max_steps_reached", step_count=82, name="trajectory_0013.json"),
        Trajectory(outcome="exit:task_complete", step_count=39, name="trajectory_0043.json"),
    ]
    cycles = [
        CycleRecord(
            cycle_no=7,
            timestamp="16:30:45Z",
            outcome="max_steps_reached",
            trajectory_path="/x/ai/trajectories/trajectory_0013.json",
        ),
        CycleRecord(
            cycle_no=8,
            timestamp="17:29:10Z",
            outcome="exit:task_complete",
            trajectory_path="/x/ai/trajectories/trajectory_0043.json",
        ),
        # A wall-clock kill: no OUTER lines, trajectory_path is None.
        CycleRecord(cycle_no=9, timestamp="23:23:29Z", outcome=None, trajectory_path=None),
        # Last cycle in file order; its start is after midnight (wrap from cycle 9).
        CycleRecord(
            cycle_no=10,
            timestamp="00:17:48Z",
            outcome="exit:task_complete",
            trajectory_path="/x/ai/trajectories/trajectory_0043.json",
        ),
    ]
    return Run(trajectories=trajectories, cycles=cycles)


def test_join_by_basename() -> None:
    """A cycle joins its trajectory by the basename of trajectory_path."""
    m = _metrics_by_cycle(_sample_run())[7]
    assert m.trajectory_name == "trajectory_0013.json"
    assert m.step_count == 82
    assert m.outcome == "max_steps_reached"


def test_kill_no_join() -> None:
    """A kill (trajectory_path None) joins no trajectory: step_count 0, name None."""
    m = _metrics_by_cycle(_sample_run())[9]
    assert m.step_count == 0
    assert m.trajectory_name is None
    assert m.outcome is None


def test_duration_start_to_next_start() -> None:
    """duration_seconds is the gap to the next cycle's start (16:30:45 -> 17:29:10)."""
    m = _metrics_by_cycle(_sample_run())[7]
    assert m.duration_seconds == 3505


def test_midnight_wrap() -> None:
    """A negative raw diff (23:23:29 -> 00:17:48) wraps to a positive duration."""
    m = _metrics_by_cycle(_sample_run())[9]
    assert m.duration_seconds == 3259
    assert m.duration_seconds > 0


def test_last_cycle_duration_none() -> None:
    """The last cycle in file order has no following start: duration_seconds None."""
    m = _metrics_by_cycle(_sample_run())[10]
    assert m.duration_seconds is None


def test_output_sorted_by_cycle_no() -> None:
    """Output is sorted by cycle_no even when file order is not."""
    trajectories = [Trajectory(outcome="x", step_count=5, name="t.json")]
    cycles = [
        CycleRecord(cycle_no=10, timestamp="00:00:00Z", outcome="x",
                    trajectory_path="/x/t.json"),
        CycleRecord(cycle_no=7, timestamp="00:00:00Z", outcome="x",
                    trajectory_path="/x/t.json"),
        CycleRecord(cycle_no=8, timestamp="00:00:00Z", outcome="x",
                    trajectory_path="/x/t.json"),
    ]
    run = Run(trajectories=trajectories, cycles=cycles)
    result = build_cycle_metrics(run)
    assert [m.cycle_no for m in result] == [7, 8, 10]


def test_no_mutation_and_determinism() -> None:
    """build_cycle_metrics never mutates its input and is deterministic."""
    run = _sample_run()
    before = copy.deepcopy(run.cycles)
    first = build_cycle_metrics(run)
    second = build_cycle_metrics(run)
    assert first == second
    assert run.cycles == before
    # The returned metrics are independent value objects.
    assert all(isinstance(m, CycleMetrics) for m in first)


def test_real_seed_metrics(seed_dir) -> None:
    """The real seed: 22 cycles with the documented per-cycle metrics."""
    run = load_run(seed_dir)
    metrics = build_cycle_metrics(run)
    assert len(metrics) == 22

    by = {m.cycle_no: m for m in metrics}

    c7 = by[7]
    assert c7.step_count == 82
    assert c7.duration_seconds == 3505
    assert c7.trajectory_name == "trajectory_0013.json"

    c19 = by[19]
    assert c19.duration_seconds == 3259  # the midnight wrap (23:23:29 -> 00:17:48)

    for no in (21, 22, 25):
        m = by[no]
        assert m.step_count == 0
        assert m.duration_seconds == 3600
        assert m.trajectory_name is None

    c28 = by[28]
    assert c28.duration_seconds is None
    assert c28.step_count == 39
    assert c28.trajectory_name == "trajectory_0043.json"
