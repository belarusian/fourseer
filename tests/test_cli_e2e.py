"""End-to-end tests that drive the CLI as a REAL subprocess.

Unlike :mod:`tests.test_cli` (which calls :func:`fourseer.cli.main` in-process),
these tests spawn the actual entrypoint a user runs -- ``python -m fourseer``
(``fourseer/__main__.py``) -- via :func:`subprocess.run`, so the process
boundary (argv parsing, stdout/stderr separation, real exit code) is observed.

The three subcommand tests are gated on the ``seed_dir`` fixture (they skip
when the local-only seed dataset is absent) and each pins a small, stable
stdout slice derived from the real seed. The missing-dir test needs no seed:
it runs against a nonexistent path and asserts the exit-code contract.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Spawn ``python -m fourseer <args...>`` and capture stdout/stderr."""
    return subprocess.run(
        [sys.executable, "-m", "fourseer", *args],
        capture_output=True,
        text=True,
    )


# --- report -----------------------------------------------------------------
def test_e2e_report_subprocess(seed_dir: Path) -> None:
    """``python -m fourseer report <seed>`` exits 0 and prints the metrics header."""
    proc = _run_cli("report", str(seed_dir))
    assert proc.returncode == 0
    assert "# Per-Cycle Metrics (22 cycles)" in proc.stdout
    assert "| 7 | max_steps_reached | 82 | 3505 | trajectory_0013.json |" in proc.stdout


# --- taxonomy ---------------------------------------------------------------
def test_e2e_taxonomy_subprocess(seed_dir: Path) -> None:
    """``python -m fourseer taxonomy <seed>`` exits 0 and prints the distribution."""
    proc = _run_cli("taxonomy", str(seed_dir))
    assert proc.returncode == 0
    assert "modes: max_steps=7, task_complete=12, wall_clock_kill=3" in proc.stdout
    assert "gates: green=20, unknown=2" in proc.stdout
    assert "merged: merged=20, unknown=2" in proc.stdout


# --- drift ------------------------------------------------------------------
def test_e2e_drift_subprocess(seed_dir: Path) -> None:
    """``python -m fourseer drift <seed>`` exits 0 and prints the plan-drift rows."""
    proc = _run_cli("drift", str(seed_dir))
    assert proc.returncode == 0
    assert "# Plan Drift (14 cycles)" in proc.stdout
    assert "cycle 1: planned_not_executed" in proc.stdout
    assert "cycle 28: executed_not_planned" in proc.stdout


# --- missing dir (no seed required) -----------------------------------------
def test_e2e_missing_dir_nonzero_and_stderr(tmp_path: Path) -> None:
    """A nonexistent AI dir exits 2, prints the error to stderr, and empty stdout."""
    missing = tmp_path / "does-not-exist"
    proc = _run_cli("report", str(missing))
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "not a directory" in proc.stderr


# --- taxonomy on the committed launch-gate golden fixture (no seed required) --
def test_e2e_taxonomy_landed_golden_fixture() -> None:
    """``python -m fourseer taxonomy <launch-gate fixture>`` reports cycle 2 as
    lost and cycle 5 as landed, with gates:/merged: populated (not ``-``)."""
    fixture = Path(__file__).parent / "fixtures" / "launch_gate"
    proc = _run_cli("taxonomy", str(fixture))
    assert proc.returncode == 0
    # The landed/lost dimension distinguishes the two wall-clock kills.
    assert "landed/lost: landed=1, lost=1" in proc.stdout
    # gates:/merged: are populated from the launch-gate dialect (not ``-``).
    assert "gates: green=1, unknown=1" in proc.stdout
    assert "merged: merged=1, unknown=1" in proc.stdout


# --- report on the committed launch-gate golden fixture (no seed required) ----
def test_e2e_report_landed_golden_fixture() -> None:
    """``python -m fourseer report <launch-gate fixture>`` renders a ``Landed``
    column showing cycle 2 as lost and cycle 5 as landed."""
    fixture = Path(__file__).parent / "fixtures" / "launch_gate"
    proc = _run_cli("report", str(fixture))
    assert proc.returncode == 0
    assert "| Cycle | Outcome | Steps | Duration (s) | Trajectory | Landed |" in proc.stdout
    assert "| 2 | - | 0 | 7819 | - | lost |" in proc.stdout
    assert "| 5 | - | 0 | - | - | landed |" in proc.stdout
