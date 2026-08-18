"""Tests for :func:`fourseer.parse.trajectories.load_trajectories`.

Covers the tolerant loader (TICKET-002): missing/extra keys, derived
``step_count``, corrupt-file skipping, and deterministic sorted order. Uses
small inline fixtures plus one test against the real seed dataset.
"""

from __future__ import annotations

import json
from pathlib import Path

from fourseer.parse.trajectories import load_trajectories


def _write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_inline_fixture_dir(tmp_path: Path) -> None:
    """A dir of small JSON files: derived step_count, explicit step_count,
    missing outcome, extra keys, and sorted order."""
    # 0000: missing outcome, 2 messages -> step_count derived to 2.
    _write(tmp_path / "trajectory_0000.json", {"messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]})
    # 0001: explicit step_count honored, extra top-level key ignored.
    _write(tmp_path / "trajectory_0001.json", {"outcome": "exit:task_complete", "messages": [{"role": "user", "content": "x"}], "step_count": 99, "extra": "ignored"})
    # 0002: missing messages -> [] and step_count 0.
    _write(tmp_path / "trajectory_0002.json", {"outcome": "max_steps_reached"})

    trajs = load_trajectories(tmp_path)
    assert len(trajs) == 3

    t0, t1, t2 = trajs
    assert t0.outcome is None
    assert t0.step_count == 2
    assert t0.messages == [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]

    assert t1.outcome == "exit:task_complete"
    assert t1.step_count == 99  # explicit int honored
    assert t1.messages == [{"role": "user", "content": "x"}]

    assert t2.outcome == "max_steps_reached"
    assert t2.messages == []
    assert t2.step_count == 0


def test_corrupt_file_skipped(tmp_path: Path) -> None:
    """A non-JSON file is skipped, not raised; valid files still load."""
    (tmp_path / "trajectory_0000.json").write_text("this is not json {", encoding="utf-8")
    _write(tmp_path / "trajectory_0001.json", {"outcome": "exit:task_complete", "messages": [{"role": "user", "content": "ok"}]})
    # A JSON file that is not a dict (a bare list) is also skipped.
    (tmp_path / "trajectory_0002.json").write_text("[1, 2, 3]", encoding="utf-8")

    trajs = load_trajectories(tmp_path)
    assert len(trajs) == 1
    assert trajs[0].outcome == "exit:task_complete"
    assert trajs[0].step_count == 1


def test_single_file(tmp_path: Path) -> None:
    """A single .json file yields a one-element list."""
    f = tmp_path / "trajectory_0000.json"
    _write(f, {"outcome": "max_steps_reached", "messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]})
    trajs = load_trajectories(f)
    assert len(trajs) == 1
    assert trajs[0].outcome == "max_steps_reached"
    assert trajs[0].step_count == 2


def test_non_dict_messages_filtered(tmp_path: Path) -> None:
    """Non-dict message entries are dropped; step_count reflects the kept ones."""
    f = tmp_path / "trajectory_0000.json"
    _write(f, {"outcome": "x", "messages": [{"role": "user", "content": "a"}, "not-a-dict", 42]})
    trajs = load_trajectories(f)
    assert trajs[0].messages == [{"role": "user", "content": "a"}]
    assert trajs[0].step_count == 1


def test_seed_trajectories(seed_dir: Path) -> None:
    """Real seed: 44 trajectories; first is max_steps_reached with 122 steps."""
    trajs = load_trajectories(seed_dir / "trajectories")
    assert len(trajs) == 44
    first = trajs[0]
    assert first.outcome == "max_steps_reached"
    assert first.step_count == 122
    assert len(first.messages) == 122
