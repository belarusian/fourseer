"""Tests for :mod:`fourseer.cli`.

Covers the ``fourseer`` entrypoint: the three subcommands (``report`` /
``taxonomy`` / ``drift``) each print the expected block to stdout and return
``0``; a missing / non-directory AI dir returns a non-zero code with a short
stderr message (and empty stdout); and subcommand dispatch is correct. Most
tests use a small INLINE temp-dir fixture (a minimal AI dir with a tiny
``cycles.out`` + ``gate-log.md`` + ``trajectories/``), NOT the full seed.
Exactly one test exercises the real seed dataset via the ``seed_dir`` fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from fourseer.cli import main

# --- Inline fixture content -------------------------------------------------
# A minimal run: cycles 1 (completed), 2 (wall-clock kill), 3 (completed).
# The Build Order plans cycles 1-2 and 5-6, so plan drift surfaces cycle 3
# (executed_not_planned) and cycles 5/6 (planned_not_executed).
_CYCLES_OUT = (
    "========== CYCLE 1  10:00:00Z ==========\n"
    "OUTER trajectory saved to: /x/ai/trajectories/trajectory_0001.json\n"
    "OUTER outcome: exit:task_complete\n"
    "========== CYCLE 1 done ==========\n"
    "========== CYCLE 2  11:00:00Z ==========\n"
    "========== CYCLE 2 done ==========\n"
    "========== CYCLE 3  12:00:00Z ==========\n"
    "OUTER trajectory saved to: /x/ai/trajectories/trajectory_0003.json\n"
    "OUTER outcome: exit:task_complete\n"
    "========== CYCLE 3 done ==========\n"
)

_GATE_LOG = (
    "# Gate Log\n"
    "\n"
    "## Build Order\n"
    "\n"
    "| Phase | Cycles | Target |\n"
    "| --- | --- | --- |\n"
    "| Foundations | 1-2 | parse |\n"
    "| Report | 5-6 | metrics |\n"
    "\n"
    "## Cycle 1: Foundations\n"
    "\n"
    "**Date:** 2026-01-01\n"
)

_TRAJECTORIES: dict[str, dict[str, Any]] = {
    "trajectory_0001.json": {
        "outcome": "exit:task_complete",
        "messages": [{"role": "user", "content": "hi"}],
    },
    "trajectory_0003.json": {
        "outcome": "exit:task_complete",
        "messages": [{"role": "user", "content": "hi"}],
    },
}


def _write_ai_dir(root: Path) -> Path:
    """Write a minimal AI-artifact directory under *root* and return its path."""
    ai = root / "ai"
    (ai / "trajectories").mkdir(parents=True)
    (ai / "cycles.out").write_text(_CYCLES_OUT, encoding="utf-8")
    (ai / "gate-log.md").write_text(_GATE_LOG, encoding="utf-8")
    for name, payload in _TRAJECTORIES.items():
        (ai / "trajectories" / name).write_text(json.dumps(payload), encoding="utf-8")
    return ai


@pytest.fixture
def ai_dir(tmp_path: Path) -> Path:
    """A small inline AI-artifact directory (NOT the full seed)."""
    return _write_ai_dir(tmp_path)


# --- report -----------------------------------------------------------------
def test_report_prints_metrics_table(ai_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["report", str(ai_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Per-Cycle Metrics (3 cycles)" in out
    # cycle 1: joined, 1 step, 3600s to cycle 2 start
    assert "| 1 | exit:task_complete | 1 | 3600 | trajectory_0001.json |" in out
    # cycle 2: a kill -> outcome/trajectory placeholders, 3600s to cycle 3 start
    assert "| 2 | - | 0 | 3600 | - |" in out
    # cycle 3: last cycle -> duration placeholder
    assert "| 3 | exit:task_complete | 1 | - | trajectory_0003.json |" in out


# --- taxonomy ---------------------------------------------------------------
def test_taxonomy_prints_distribution(ai_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["taxonomy", str(ai_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Failure-Mode Taxonomy (3 cycles)" in out
    assert "cycles: 3" in out
    assert "modes: task_complete=2, wall_clock_kill=1" in out
    # No Results tables in the fixture -> no gate/merged counts, so both
    # render as the bare placeholder (the unknown suffix is only shown when
    # a count dict is non-empty, per render_taxonomy).
    assert "gates: -" in out
    assert "merged: -" in out


# --- drift ------------------------------------------------------------------
def test_drift_prints_plan_drift(ai_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["drift", str(ai_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Plan Drift (3 cycles)" in out
    # cycle 3 ran but was never planned; cycles 5/6 planned but never ran.
    assert "cycle 3: executed_not_planned" in out
    assert "cycle 5: planned_not_executed" in out
    assert "cycle 6: planned_not_executed" in out


# --- dispatch ---------------------------------------------------------------
def test_subcommand_dispatch_is_distinct(ai_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Each subcommand prints its own block (headers are mutually exclusive)."""
    assert main(["report", str(ai_dir)]) == 0
    report = capsys.readouterr().out
    assert "Per-Cycle Metrics" in report
    assert "Failure-Mode Taxonomy" not in report
    assert "Plan Drift" not in report

    assert main(["taxonomy", str(ai_dir)]) == 0
    taxonomy = capsys.readouterr().out
    assert "Failure-Mode Taxonomy" in taxonomy
    assert "Per-Cycle Metrics" not in taxonomy
    assert "Plan Drift" not in taxonomy

    assert main(["drift", str(ai_dir)]) == 0
    drift = capsys.readouterr().out
    assert "Plan Drift" in drift
    assert "Per-Cycle Metrics" not in drift
    assert "Failure-Mode Taxonomy" not in drift


# --- error handling ---------------------------------------------------------
def test_missing_dir_returns_nonzero_and_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "does-not-exist"
    rc = main(["report", str(missing)])
    assert rc != 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "not a directory" in captured.err
    assert str(missing) in captured.err


def test_missing_dir_nonzero_for_every_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = str(tmp_path / "nope")
    for cmd in ("report", "taxonomy", "drift"):
        assert main([cmd, missing]) != 0
        capsys.readouterr()  # drain


def test_path_that_is_a_file_returns_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a_file = tmp_path / "cycles.out"
    a_file.write_text("not a directory\n", encoding="utf-8")
    rc = main(["report", str(a_file)])
    assert rc != 0
    assert "not a directory" in capsys.readouterr().err


# --- real seed --------------------------------------------------------------
def test_real_seed_cli(seed_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Run all three subcommands against the real seed and pin a stable slice.

    Derived by running the CLI against the seed: 22 cycles (7-28), 3 kills
    (21/22/25), 14 plan-drift rows (1-6 planned_not_executed, 21-28
    executed_not_planned).
    """
    # report
    assert main(["report", str(seed_dir)]) == 0
    report = capsys.readouterr().out
    assert "# Per-Cycle Metrics (22 cycles)" in report
    assert "| 7 | max_steps_reached | 82 | 3505 | trajectory_0013.json |" in report

    # taxonomy
    assert main(["taxonomy", str(seed_dir)]) == 0
    taxonomy = capsys.readouterr().out
    assert "# Failure-Mode Taxonomy (22 cycles)" in taxonomy
    assert "modes: max_steps=7, task_complete=12, wall_clock_kill=3" in taxonomy
    assert "gates: green=20, unknown=2" in taxonomy
    assert "merged: merged=20, unknown=2" in taxonomy

    # drift
    assert main(["drift", str(seed_dir)]) == 0
    drift = capsys.readouterr().out
    assert "# Plan Drift (14 cycles)" in drift
    assert "cycle 1: planned_not_executed" in drift
    assert "cycle 28: executed_not_planned" in drift
