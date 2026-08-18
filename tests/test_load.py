"""Tests for :func:`fourseer.load.load_run`.

Uses small inline temp-dir fixtures to exercise the composition of the four
parsers and the tolerance of missing optional files, plus exactly ONE test
against the real seed dataset (TICKET-007).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from fourseer.load import load_run
from fourseer.models import GateLog, Run

TRAJ_JSON = '{"outcome": "exit:task_complete", "messages": [{"role": "user", "content": "hi"}]}'
CYCLES_OUT = """\
========== CYCLE 7  16:30:45Z ==========
OUTER trajectory saved to: /tmp/ai/trajectories/trajectory_0013.json
OUTER outcome: max_steps_reached
========== CYCLE 21  01:12:49Z ==========
./run-cycles.sh: line 19: Alarm clock
"""
GATE_LOG = """\
# Gate Log

## Build Order

| Phase | Cycles | Target |
|-------|--------|--------|
| Foundations | 1-3 | Session log |

## Cycle 7: Foundations

**Date:** 2026-08-17
"""


def _write_ai_dir(tmp_path: Path, *, traj: bool = True, cycles: bool = True, gate: bool = True) -> Path:
    """Populate a temp ai_dir with the requested artifacts."""
    if traj:
        tdir = tmp_path / "trajectories"
        tdir.mkdir()
        (tdir / "trajectory_0001.json").write_text(TRAJ_JSON, encoding="utf-8")
    if cycles:
        (tmp_path / "cycles.out").write_text(CYCLES_OUT, encoding="utf-8")
    if gate:
        (tmp_path / "gate-log.md").write_text(GATE_LOG, encoding="utf-8")
    return tmp_path


def test_load_run_full(tmp_path: Path) -> None:
    """All three artifacts present -> Run carries all of them."""
    _write_ai_dir(tmp_path)
    run = load_run(tmp_path)
    assert isinstance(run, Run)
    assert run.trajectory_count == 1
    assert run.trajectories[0].outcome == "exit:task_complete"
    assert run.cycle_count == 2
    assert run.cycles[0].outcome == "max_steps_reached"
    assert run.cycles[1].outcome is None
    assert run.killed_cycles() == [21]
    assert len(run.gate_log.build_order) == 1
    assert run.gate_log.build_order[0].phase == "Foundations"
    assert len(run.gate_log.cycles) == 1
    assert run.commits == []


def test_load_run_empty_dir(tmp_path: Path) -> None:
    """A directory with no artifacts -> all-empty Run (tolerant)."""
    run = load_run(tmp_path)
    assert run.trajectory_count == 0
    assert run.cycle_count == 0
    assert run.gate_log == GateLog()
    assert run.commits == []


def test_load_run_missing_optional_files(tmp_path: Path) -> None:
    """Each missing optional file independently yields an empty result."""
    # Only cycles.out present.
    _write_ai_dir(tmp_path, traj=False, gate=False)
    run = load_run(tmp_path)
    assert run.trajectory_count == 0
    assert run.cycle_count == 2
    assert run.gate_log == GateLog()

    # Only gate-log.md present.
    tmp2 = tmp_path / "only-gate"
    tmp2.mkdir()
    (tmp2 / "gate-log.md").write_text(GATE_LOG, encoding="utf-8")
    run2 = load_run(tmp2)
    assert run2.trajectory_count == 0
    assert run2.cycle_count == 0
    assert len(run2.gate_log.build_order) == 1


def test_load_run_accepts_str_paths(tmp_path: Path) -> None:
    """ai_dir may be a str, not just a Path."""
    _write_ai_dir(tmp_path)
    run = load_run(str(tmp_path))
    assert run.trajectory_count == 1
    assert run.cycle_count == 2


def test_load_run_reads_git_history_when_repo_given(tmp_path: Path) -> None:
    """When repo_path is a git repo, its commits are read into Run.commits."""
    _write_ai_dir(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True, env=env)

    run = load_run(tmp_path, repo_path=repo)
    assert len(run.commits) == 1
    assert run.commits[0].subject == "init"


def test_load_run_omits_repo_when_none(tmp_path: Path) -> None:
    """repo_path=None (default) -> commits empty, no git call made."""
    _write_ai_dir(tmp_path)
    run = load_run(tmp_path)
    assert run.commits == []


def test_load_run_raises_for_bad_repo(tmp_path: Path) -> None:
    """An explicitly-passed repo path that is not a git repo raises."""
    _write_ai_dir(tmp_path)
    not_repo = tmp_path / "not-a-repo"
    not_repo.mkdir()
    with pytest.raises(RuntimeError):
        load_run(tmp_path, repo_path=not_repo)


def test_load_run_seed(seed_dir: Path) -> None:
    """Real seed: 44 trajectories, 22 cycle records, 6 build-order rows,
    26 cycle blocks, killed cycles == [21, 22, 25]."""
    run = load_run(seed_dir)
    assert run.trajectory_count == 44
    assert run.cycle_count == 22
    assert len(run.gate_log.build_order) == 6
    assert len(run.gate_log.cycles) == 26
    assert run.killed_cycles() == [21, 22, 25]
    # No repo supplied -> commits empty.
    assert run.commits == []
