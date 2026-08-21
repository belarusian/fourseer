"""Tests for :mod:`fourseer.report`.

Covers :func:`fourseer.report.build_cycle_metrics` (basename join, kill
no-join, start-to-next duration, midnight wrap, last-cycle ``None`` duration,
``cycle_no`` ordering, no-mutation / determinism),
:func:`fourseer.report.render_report` (header, placeholder rendering, row
order, determinism, no mutation), and
:func:`fourseer.report.extract_tokens_cost` (conservative extraction, no
false-positives on incidental prose), :func:`fourseer.report.summarize_run`
(run-level aggregation, join over the set of referenced trajectory names),
and :func:`fourseer.report.render_summary` (deterministic block, ``-``
placeholder for ``None`` tokens/cost). Most tests use small hand-built inline
fixtures (not the full seed). Exactly one test per function exercises the real
seed dataset via the ``seed_dir`` fixture.
"""

from __future__ import annotations

import copy

import pytest

from fourseer.load import load_run
from fourseer.models import CycleMetrics, CycleRecord, Run, RunSummary, Trajectory
from fourseer.report import (
    build_cycle_metrics,
    extract_tokens_cost,
    render_report,
    render_summary,
    summarize_run,
)


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


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


def _cm(cycle_no, outcome, step_count, duration_seconds, trajectory_name):
    """Build a CycleMetrics value (positional shortcut for tests)."""
    return CycleMetrics(
        cycle_no=cycle_no,
        outcome=outcome,
        step_count=step_count,
        duration_seconds=duration_seconds,
        trajectory_name=trajectory_name,
    )


def test_render_report_header_and_empty() -> None:
    """An empty list renders the (0 cycles) header + table header, no rows."""
    text = render_report([])
    lines = text.splitlines()
    assert lines[0] == "# Per-Cycle Metrics (0 cycles)"
    assert "| Cycle | Outcome | Steps | Duration (s) | Trajectory |" in lines
    assert "| --- | --- | --- | --- | --- |" in lines
    # No data rows.
    assert not any(line.startswith("| ") and line != "| --- | --- | --- | --- | --- |"
                   and "Cycle" not in line for line in lines[3:])


def test_render_report_kill_row_placeholders() -> None:
    """A kill (outcome None, trajectory_name None) renders '-' in those columns."""
    text = render_report([_cm(21, None, 0, 3600, None)])
    assert "| 21 | - | 0 | 3600 | - |" in text


def test_render_report_last_cycle_duration_placeholder() -> None:
    """The last cycle (duration_seconds None) renders '-' in the duration column."""
    text = render_report([_cm(28, "exit:task_complete", 39, None, "trajectory_0043.json")])
    assert "| 28 | exit:task_complete | 39 | - | trajectory_0043.json |" in text


def test_render_report_preserves_given_order() -> None:
    """Rows appear in the GIVEN order; the renderer does NOT re-sort."""
    metrics = [
        _cm(10, "x", 1, 10, "t10.json"),
        _cm(7, "x", 2, 20, "t7.json"),
        _cm(8, "x", 3, 30, "t8.json"),
    ]
    text = render_report(metrics)
    lines = text.splitlines()
    # The three data rows, in input order 10, 7, 8.
    data_rows = [line for line in lines if line.startswith("| ") and "Cycle" not in line
                 and "---" not in line]
    assert data_rows == [
        "| 10 | x | 1 | 10 | t10.json |",
        "| 7 | x | 2 | 20 | t7.json |",
        "| 8 | x | 3 | 30 | t8.json |",
    ]


def test_render_report_deterministic_and_no_mutation() -> None:
    """render_report is deterministic and never mutates its input."""
    metrics = [
        _cm(7, "max_steps_reached", 82, 3505, "trajectory_0013.json"),
        _cm(21, None, 0, 3600, None),
    ]
    before = [m for m in metrics]  # shallow snapshot of the same objects
    first = render_report(metrics)
    second = render_report(metrics)
    assert first == second
    # The list order and the (frozen) values are unchanged.
    assert [m.cycle_no for m in metrics] == [m.cycle_no for m in before]
    assert metrics == before


def test_render_report_header_count() -> None:
    """The header line states the exact cycle count."""
    metrics = [_cm(i, "x", i, i, f"t{i}.json") for i in range(1, 6)]
    text = render_report(metrics)
    assert text.splitlines()[0] == "# Per-Cycle Metrics (5 cycles)"


# ---------------------------------------------------------------------------
# extract_tokens_cost
# ---------------------------------------------------------------------------


def test_extract_tokens_cost_with_cost() -> None:
    """A 'usage: tokens=N cost=C' line yields (N, C)."""
    traj = Trajectory(outcome="x", messages=[
        {"role": "user", "content": "usage: tokens=123 cost=0.45"},
    ])
    assert extract_tokens_cost(traj) == (123, 0.45)


def test_extract_tokens_cost_tokens_only() -> None:
    """A 'usage: tokens=N' line (no cost) yields (N, None)."""
    traj = Trajectory(outcome="x", messages=[
        {"role": "user", "content": "usage: tokens=500"},
    ])
    assert extract_tokens_cost(traj) == (500, None)


def test_extract_tokens_cost_no_false_positive_on_prose() -> None:
    """Incidental prose never matches: shell usage(), TS type decls, usage in comments."""
    prose = "\n".join([
        "usage() {",
        "    echo \"Usage: $0 [OPTIONS]\"",
        "}",
        "FIVE_MAX_TOKENS=65536",
        "export interface TokenUsage {",
        "  prompt_tokens: number;",
        "  completion_tokens: number;",
        "}",
        "// Carries the step usage when the adapter reported token accounting.",
    ])
    traj = Trajectory(outcome="x", messages=[{"role": "user", "content": prose}])
    assert extract_tokens_cost(traj) == (None, None)


def test_extract_tokens_cost_sums_multiple_records() -> None:
    """Multiple usage records across messages are summed (tokens and cost)."""
    traj = Trajectory(outcome="x", messages=[
        {"role": "user", "content": "usage: tokens=100 cost=0.10"},
        {"role": "user", "content": "noise\nusage: tokens=200 cost=0.20\nmore"},
        {"role": "user", "content": "usage: tokens=50"},
    ])
    tokens, cost = extract_tokens_cost(traj)
    assert tokens == 350
    assert cost == pytest.approx(0.30)


def test_extract_tokens_cost_empty_trajectory() -> None:
    """A trajectory with no messages yields (None, None)."""
    assert extract_tokens_cost(Trajectory(outcome="x")) == (None, None)


def test_extract_tokens_cost_no_mutation() -> None:
    """extract_tokens_cost never mutates the trajectory's messages."""
    messages = [{"role": "user", "content": "usage: tokens=10 cost=0.01"}]
    traj = Trajectory(outcome="x", messages=messages)
    before = [dict(m) for m in messages]
    extract_tokens_cost(traj)
    assert traj.messages == before


def test_real_seed_report(seed_dir) -> None:
    """The real seed: render build_cycle_metrics(load_run(seed_dir)) and pin a slice."""
    run = load_run(seed_dir)
    text = render_report(build_cycle_metrics(run))
    lines = text.splitlines()

    # Header line.
    assert lines[0] == "# Per-Cycle Metrics (22 cycles)"

    # A normal row (cycle 7).
    assert "| 7 | max_steps_reached | 82 | 3505 | trajectory_0013.json |" in lines

    # A wall-clock-kill row (cycle 21): outcome and trajectory render as '-'.
    assert "| 21 | - | 0 | 3600 | - |" in lines

    # The last cycle (28): duration renders as '-'.
    assert "| 28 | exit:task_complete | 39 | - | trajectory_0043.json |" in lines

    # Exactly 22 data rows.
    data_rows = [line for line in lines if line.startswith("| ") and "Cycle" not in line
                 and "---" not in line]
    assert len(data_rows) == 22

# ---------------------------------------------------------------------------
# summarize_run
# ---------------------------------------------------------------------------


def _cm(cycle_no, outcome, step_count, duration_seconds, trajectory_name):
    return CycleMetrics(
        cycle_no=cycle_no,
        outcome=outcome,
        step_count=step_count,
        duration_seconds=duration_seconds,
        trajectory_name=trajectory_name,
    )


def test_summarize_run_empty_metrics() -> None:
    """Empty metrics: all counts/sums zero, tokens/cost None."""
    s = summarize_run([])
    assert s == RunSummary(0, 0, 0, 0, 0, 0, None, None)


def test_summarize_run_all_completed() -> None:
    """Every cycle has a non-None outcome: completed_count == cycle_count."""
    metrics = [
        _cm(1, "exit:task_complete", 10, 100, "a.json"),
        _cm(2, "max_steps_reached", 20, 200, "b.json"),
    ]
    s = summarize_run(metrics)
    assert s.cycle_count == 2
    assert s.completed_count == 2
    assert s.killed_count == 0
    assert s.total_steps == 30
    assert s.total_duration_seconds == 300
    assert s.cycles_with_duration == 2


def test_summarize_run_all_killed() -> None:
    """Every cycle has outcome None: killed_count == cycle_count."""
    metrics = [
        _cm(1, None, 0, 100, None),
        _cm(2, None, 0, 200, None),
        _cm(3, None, 0, None, None),
    ]
    s = summarize_run(metrics)
    assert s.cycle_count == 3
    assert s.completed_count == 0
    assert s.killed_count == 3
    assert s.total_steps == 0
    assert s.total_duration_seconds == 300
    assert s.cycles_with_duration == 2


def test_summarize_run_mixed() -> None:
    """A mix of completed and killed cycles partitions the total."""
    metrics = [
        _cm(1, "exit:task_complete", 10, 100, "a.json"),
        _cm(2, None, 0, 200, None),
        _cm(3, "max_steps_reached", 5, None, "b.json"),
    ]
    s = summarize_run(metrics)
    assert s.cycle_count == 3
    assert s.completed_count == 2
    assert s.killed_count == 1
    assert s.completed_count + s.killed_count == s.cycle_count
    assert s.total_steps == 15
    assert s.total_duration_seconds == 300
    assert s.cycles_with_duration == 2


def test_summarize_run_last_cycle_none_duration() -> None:
    """A None duration (last cycle) is excluded from the sum and count."""
    metrics = [
        _cm(1, "x", 10, 100, "a.json"),
        _cm(2, "x", 20, None, "b.json"),
    ]
    s = summarize_run(metrics)
    assert s.total_duration_seconds == 100
    assert s.cycles_with_duration == 1


def test_summarize_run_trajectories_none() -> None:
    """trajectories=None: tokens/cost are None even if metrics reference names."""
    metrics = [_cm(1, "x", 10, 100, "a.json")]
    s = summarize_run(metrics, None)
    assert s.total_tokens is None
    assert s.total_cost is None


def test_summarize_run_joined_trajectory_with_usage() -> None:
    """A referenced trajectory carrying a usage record contributes tokens/cost."""
    metrics = [
        _cm(1, "x", 10, 100, "a.json"),
        _cm(2, "x", 20, 200, "b.json"),
    ]
    trajectories = [
        Trajectory(outcome="x", step_count=10, name="a.json",
                   messages=[{"role": "user", "content": "usage: tokens=100 cost=0.5"}]),
        Trajectory(outcome="x", step_count=20, name="b.json",
                   messages=[{"role": "user", "content": "usage: tokens=200 cost=0.25"}]),
    ]
    s = summarize_run(metrics, trajectories)
    assert s.total_tokens == 300
    assert s.total_cost == pytest.approx(0.75)


def test_summarize_run_referenced_by_two_cycles_counted_once() -> None:
    """A trajectory referenced by two cycles contributes its tokens/cost ONCE."""
    metrics = [
        _cm(1, "x", 10, 100, "a.json"),
        _cm(2, "x", 20, 200, "a.json"),
    ]
    trajectories = [
        Trajectory(outcome="x", step_count=10, name="a.json",
                   messages=[{"role": "user", "content": "usage: tokens=100 cost=0.5"}]),
    ]
    s = summarize_run(metrics, trajectories)
    assert s.total_tokens == 100
    assert s.total_cost == pytest.approx(0.5)


def test_summarize_run_unreferenced_trajectory_not_counted() -> None:
    """A trajectory in the list but referenced by no cycle contributes nothing."""
    metrics = [_cm(1, "x", 10, 100, "a.json")]
    trajectories = [
        Trajectory(outcome="x", step_count=10, name="a.json",
                   messages=[{"role": "user", "content": "usage: tokens=100 cost=0.5"}]),
        Trajectory(outcome="x", step_count=99, name="orphan.json",
                   messages=[{"role": "user", "content": "usage: tokens=999 cost=9.9"}]),
    ]
    s = summarize_run(metrics, trajectories)
    assert s.total_tokens == 100
    assert s.total_cost == pytest.approx(0.5)


def test_summarize_run_no_usage_records_yields_none() -> None:
    """Referenced trajectories without usage records: tokens/cost stay None."""
    metrics = [_cm(1, "x", 10, 100, "a.json")]
    trajectories = [
        Trajectory(outcome="x", step_count=10, name="a.json",
                   messages=[{"role": "user", "content": "no usage here"}]),
    ]
    s = summarize_run(metrics, trajectories)
    assert s.total_tokens is None
    assert s.total_cost is None


def test_summarize_run_deterministic_and_no_mutation() -> None:
    """summarize_run is deterministic and never mutates its inputs."""
    metrics = [
        _cm(1, "x", 10, 100, "a.json"),
        _cm(2, None, 0, 200, None),
    ]
    trajectories = [
        Trajectory(outcome="x", step_count=10, name="a.json",
                   messages=[{"role": "user", "content": "usage: tokens=100 cost=0.5"}]),
    ]
    metrics_before = [m for m in metrics]
    traj_before = [t for t in trajectories]
    first = summarize_run(metrics, trajectories)
    second = summarize_run(metrics, trajectories)
    assert first == second
    assert metrics == metrics_before
    assert trajectories == traj_before
    assert isinstance(first, RunSummary)


def test_real_seed_summary(seed_dir) -> None:
    """The real seed: the documented run-level slice (22/19/3/1002/51106/21)."""
    run = load_run(seed_dir)
    metrics = build_cycle_metrics(run)
    s = summarize_run(metrics, run.trajectories)
    assert s.cycle_count == 22
    assert s.completed_count == 19
    assert s.killed_count == 3
    assert s.total_steps == 1002
    assert s.total_duration_seconds == 51106
    assert s.cycles_with_duration == 21
    assert s.total_tokens is None
    assert s.total_cost is None


# ---------------------------------------------------------------------------
# render_summary
# ---------------------------------------------------------------------------


def test_render_summary_header_count() -> None:
    """The header line states the exact cycle count."""
    s = RunSummary(22, 19, 3, 1002, 51106, 21, None, None)
    text = render_summary(s)
    assert text.splitlines()[0] == "# Run Summary (22 cycles)"


def test_render_summary_none_tokens_cost_placeholder() -> None:
    """None tokens/cost render as the stable '-' placeholder."""
    s = RunSummary(22, 19, 3, 1002, 51106, 21, None, None)
    text = render_summary(s)
    assert "total tokens: -" in text
    assert "total cost: -" in text


def test_render_summary_values() -> None:
    """Each aggregate field renders as a key: value line."""
    s = RunSummary(5, 4, 1, 100, 3600, 4, 1234, 0.5)
    text = render_summary(s)
    lines = text.splitlines()
    assert "cycles: 5" in lines
    assert "completed: 4" in lines
    assert "killed: 1" in lines
    assert "total steps: 100" in lines
    assert "total duration (s): 3600" in lines
    assert "cycles with duration: 4" in lines
    assert "total tokens: 1234" in lines
    assert "total cost: 0.5" in lines


def test_render_summary_deterministic_and_no_mutation() -> None:
    """render_summary is deterministic and never mutates its input."""
    s = RunSummary(22, 19, 3, 1002, 51106, 21, None, None)
    first = render_summary(s)
    second = render_summary(s)
    assert first == second
    assert s == RunSummary(22, 19, 3, 1002, 51106, 21, None, None)
