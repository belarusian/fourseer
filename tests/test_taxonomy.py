"""Tests for :mod:`fourseer.taxonomy`.

Covers :func:`fourseer.taxonomy.classify_cycle` (the total outcome -> ``mode``
mapping for every closed tag, ``gate`` / ``merged`` enrichment from a matching
``CycleBlock`` vs ``None`` when absent, and that enrichment never affects
``mode``) and :func:`fourseer.taxonomy.classify_run` (classifies only the
``cycles.out`` cycles, sorted by ``cycle_no``, tolerating a missing gate-log
block, no-mutation / determinism). Most tests use small hand-built inline
fixtures (not the full seed). Exactly one test exercises the real seed dataset
via the ``seed_dir`` fixture.
"""

from __future__ import annotations

import copy

from fourseer.load import load_run
from fourseer.models import (
    CycleBlock,
    CycleClassification,
    CycleMetrics,
    CycleRecord,
    GateLog,
    Run,
)
from fourseer.taxonomy import classify_cycle, classify_run


def _metrics(cycle_no: int, outcome: str | None) -> CycleMetrics:
    """A minimal :class:`CycleMetrics` for a given cycle / outcome."""
    return CycleMetrics(
        cycle_no=cycle_no,
        outcome=outcome,
        step_count=0,
        duration_seconds=None,
        trajectory_name=None,
    )


def _gate_log(blocks: list[CycleBlock]) -> GateLog:
    return GateLog(build_order=[], cycles=blocks)


# ---------------------------------------------------------------------------
# classify_cycle: the total outcome -> mode mapping
# ---------------------------------------------------------------------------


def test_mode_wall_clock_kill() -> None:
    """outcome is None -> wall_clock_kill."""
    c = classify_cycle(_metrics(21, None))
    assert c.mode == "wall_clock_kill"
    assert c.cycle_no == 21


def test_mode_max_steps() -> None:
    """outcome == max_steps_reached -> max_steps."""
    assert classify_cycle(_metrics(7, "max_steps_reached")).mode == "max_steps"


def test_mode_task_complete() -> None:
    """outcome == exit:task_complete -> task_complete."""
    assert classify_cycle(_metrics(8, "exit:task_complete")).mode == "task_complete"


def test_mode_execution_error() -> None:
    """outcome starting with execution_error -> execution_error."""
    assert classify_cycle(_metrics(9, "execution_error: boom")).mode == "execution_error"


def test_mode_format_error() -> None:
    """outcome starting with repeated_format_error -> format_error."""
    assert classify_cycle(_metrics(10, "repeated_format_error: x")).mode == "format_error"


def test_mode_other() -> None:
    """Any other non-None outcome -> other."""
    assert classify_cycle(_metrics(11, "exit:cancelled")).mode == "other"
    assert classify_cycle(_metrics(12, "weird_outcome")).mode == "other"


# ---------------------------------------------------------------------------
# classify_cycle: gate / merged enrichment
# ---------------------------------------------------------------------------


def test_enrichment_from_matching_block() -> None:
    """A matching CycleBlock with a Results table populates gate / merged."""
    block = CycleBlock(cycle_no=8, gate_after="green", merged=True)
    c = classify_cycle(_metrics(8, "exit:task_complete"), _gate_log([block]))
    assert c.gate == "green"
    assert c.merged is True


def test_enrichment_red_gate_not_merged() -> None:
    """gate_after red and merged False are carried through."""
    block = CycleBlock(cycle_no=1, gate_after="red", merged=False)
    c = classify_cycle(_metrics(1, "exit:task_complete"), _gate_log([block]))
    assert c.gate == "red"
    assert c.merged is False


def test_enrichment_none_when_no_block() -> None:
    """No matching block leaves gate / merged None."""
    c = classify_cycle(_metrics(21, None), _gate_log([CycleBlock(cycle_no=8)]))
    assert c.gate is None
    assert c.merged is None


def test_enrichment_none_when_gate_log_none() -> None:
    """gate_log=None leaves gate / merged None."""
    c = classify_cycle(_metrics(8, "exit:task_complete"), None)
    assert c.gate is None
    assert c.merged is None


def test_enrichment_none_when_block_has_no_results() -> None:
    """A matching block with no Results table (gate_after/merged None) -> None."""
    block = CycleBlock(cycle_no=8)  # gate_after / merged default to None
    c = classify_cycle(_metrics(8, "exit:task_complete"), _gate_log([block]))
    assert c.gate is None
    assert c.merged is None


def test_enrichment_does_not_affect_mode() -> None:
    """gate / merged enrichment never changes the mode tag."""
    block = CycleBlock(cycle_no=21, gate_after="green", merged=True)
    c = classify_cycle(_metrics(21, None), _gate_log([block]))
    # A kill with a Results table is still a wall_clock_kill.
    assert c.mode == "wall_clock_kill"
    assert c.gate == "green"
    assert c.merged is True


def test_enrichment_picks_matching_cycle_no() -> None:
    """Only the block whose cycle_no matches is used."""
    blocks = [
        CycleBlock(cycle_no=7, gate_after="red", merged=False),
        CycleBlock(cycle_no=8, gate_after="green", merged=True),
    ]
    c = classify_cycle(_metrics(8, "exit:task_complete"), _gate_log(blocks))
    assert c.gate == "green"
    assert c.merged is True


# ---------------------------------------------------------------------------
# classify_cycle: purity
# ---------------------------------------------------------------------------


def test_classify_cycle_no_mutation() -> None:
    """classify_cycle does not mutate its inputs."""
    m = _metrics(8, "exit:task_complete")
    gl = _gate_log([CycleBlock(cycle_no=8, gate_after="green", merged=True)])
    m_before = copy.deepcopy(m)
    gl_before = copy.deepcopy(gl)
    classify_cycle(m, gl)
    assert m == m_before
    assert gl == gl_before


def test_classify_cycle_deterministic() -> None:
    """The same inputs always yield the same classification."""
    m = _metrics(8, "exit:task_complete")
    gl = _gate_log([CycleBlock(cycle_no=8, gate_after="green", merged=True)])
    a = classify_cycle(m, gl)
    b = classify_cycle(m, gl)
    assert a == b
    assert isinstance(a, CycleClassification)


# ---------------------------------------------------------------------------
# classify_run
# ---------------------------------------------------------------------------


def _sample_run() -> Run:
    """A small run: cycles 7-10 in cycles.out; gate log records 7 and 8 only."""
    cycles = [
        CycleRecord(cycle_no=7, timestamp="16:30:45Z", outcome="max_steps_reached"),
        CycleRecord(cycle_no=8, timestamp="17:29:10Z", outcome="exit:task_complete"),
        # A wall-clock kill: no OUTER lines.
        CycleRecord(cycle_no=9, timestamp="18:00:00Z", outcome=None),
        CycleRecord(cycle_no=10, timestamp="19:00:00Z", outcome="exit:task_complete"),
    ]
    gate_log = _gate_log(
        [
            CycleBlock(cycle_no=7, gate_after="green", merged=True),
            CycleBlock(cycle_no=8, gate_after="green", merged=True),
            # A gate-log-only cycle (not in cycles.out) that must be ignored.
            CycleBlock(cycle_no=1, gate_after="red", merged=False),
        ]
    )
    return Run(trajectories=[], cycles=cycles, gate_log=gate_log, commits=[])


def test_classify_run_only_cycles_out() -> None:
    """classify_run classifies only the cycles.out cycles (not gate-log-only ones)."""
    result = classify_run(_sample_run())
    assert [c.cycle_no for c in result] == [7, 8, 9, 10]
    # The gate-log-only cycle 1 is NOT classified.
    assert all(c.cycle_no != 1 for c in result)


def test_classify_run_sorted_by_cycle_no() -> None:
    """The result is sorted by cycle_no even if cycles.out is not in order."""
    run = _sample_run()
    shuffled = Run(
        trajectories=[],
        cycles=list(reversed(run.cycles)),
        gate_log=run.gate_log,
        commits=[],
    )
    result = classify_run(shuffled)
    assert [c.cycle_no for c in result] == [7, 8, 9, 10]


def test_classify_run_modes_and_enrichment() -> None:
    """Modes and gate/merged enrichment are correct per cycle."""
    result = {c.cycle_no: c for c in classify_run(_sample_run())}
    assert result[7].mode == "max_steps"
    assert result[7].gate == "green"
    assert result[7].merged is True
    assert result[8].mode == "task_complete"
    assert result[8].gate == "green"
    assert result[8].merged is True
    # Cycle 9 is a kill with no gate-log block -> gate/merged None.
    assert result[9].mode == "wall_clock_kill"
    assert result[9].gate is None
    assert result[9].merged is None
    # Cycle 10 has no gate-log block -> gate/merged None.
    assert result[10].mode == "task_complete"
    assert result[10].gate is None
    assert result[10].merged is None


def test_classify_run_empty() -> None:
    """An empty run classifies to an empty list."""
    assert classify_run(Run()) == []


def test_classify_run_no_mutation() -> None:
    """classify_run does not mutate the run."""
    run = _sample_run()
    before = copy.deepcopy(run)
    classify_run(run)
    assert run == before


def test_classify_run_deterministic() -> None:
    """The same run always yields the same list."""
    run = _sample_run()
    assert classify_run(run) == classify_run(run)


# ---------------------------------------------------------------------------
# Real seed dataset (exactly one test)
# ---------------------------------------------------------------------------


def test_real_seed_taxonomy(seed_dir) -> None:
    """classify_run on the real seed: a small, stable, documented slice.

    The seed's ``cycles.out`` carries 22 cycles (7-28): 12 ``task_complete``,
    7 ``max_steps``, and 3 wall-clock kills (21/22/25). Cycles 21 and 22 are
    absent from the gate log (no ``CycleBlock``), so their ``gate`` / ``merged``
    are ``None``; cycle 25 is a kill but DOES have a gate-log ``### Results``
    table, so its ``gate`` / ``merged`` are populated (``green`` / ``True``).
    """
    run = load_run(seed_dir)
    result = classify_run(run)
    by_cycle = {c.cycle_no: c for c in result}

    assert len(result) == 22
    modes = [c.mode for c in result]
    assert modes.count("task_complete") == 12
    assert modes.count("max_steps") == 7
    assert modes.count("wall_clock_kill") == 3

    # A task_complete cycle and a max_steps cycle.
    assert by_cycle[8].mode == "task_complete"
    assert by_cycle[7].mode == "max_steps"

    # The three kills.
    assert by_cycle[21].mode == "wall_clock_kill"
    assert by_cycle[22].mode == "wall_clock_kill"
    assert by_cycle[25].mode == "wall_clock_kill"

    # Cycles 21/22 are not in the gate log -> gate/merged None.
    assert by_cycle[21].gate is None
    assert by_cycle[21].merged is None
    assert by_cycle[22].gate is None
    assert by_cycle[22].merged is None

    # Cycle 25 is a kill but has a Results table -> gate/merged populated.
    assert by_cycle[25].gate == "green"
    assert by_cycle[25].merged is True

    # A completed cycle with a Results table is green / merged.
    assert by_cycle[8].gate == "green"
    assert by_cycle[8].merged is True
