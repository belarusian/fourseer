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
