"""Tests for :func:`fourseer.parse.cycles_out.parse_cycles_out`.

Covers the header-regex fix (TICKET-003): the non-capturing group around the
optional project-name prefix must be balanced so the module imports and both
header forms parse. Uses small inline fixtures plus one test against the real
seed dataset.
"""

from __future__ import annotations

from pathlib import Path

from fourseer.parse.cycles_out import parse_cycles_out

# Two completed cycles (with OUTER lines) and one wall-clock-kill cycle
# (header only, no OUTER lines) — mirrors the seed's cycles 7, 8, 21.
FIXTURE = """\
========== CYCLE 7  16:30:45Z ==========
OUTER trajectory saved to: /tmp/ai/trajectories/trajectory_0013.json
OUTER outcome: max_steps_reached
========== CYCLE 7 done ==========
========== CYCLE 8  17:29:10Z ==========
OUTER trajectory saved to: /tmp/ai/trajectories/trajectory_0015.json
OUTER outcome: exit:task_complete
========== CYCLE 8 done ==========
========== CYCLE 21  01:12:49Z ==========
./run-cycles.sh: line 19: 127162 Alarm clock             perl -e "alarm shift; exec @ARGV" 3600 python3 "$RUN"
========== CYCLE 21 done ==========
"""


def test_completed_and_kill_cycles() -> None:
    """Two completed + one wall-clock-kill cycle -> 3 records; kill has None."""
    records = parse_cycles_out(FIXTURE)
    assert len(records) == 3

    c7, c8, c21 = records
    assert c7.cycle_no == 7
    assert c7.timestamp == "16:30:45Z"
    assert c7.outcome == "max_steps_reached"
    assert c7.trajectory_path == "/tmp/ai/trajectories/trajectory_0013.json"

    assert c8.cycle_no == 8
    assert c8.timestamp == "17:29:10Z"
    assert c8.outcome == "exit:task_complete"
    assert c8.trajectory_path == "/tmp/ai/trajectories/trajectory_0015.json"

    # Wall-clock kill: header present, no OUTER lines.
    assert c21.cycle_no == 21
    assert c21.timestamp == "01:12:49Z"
    assert c21.outcome is None
    assert c21.trajectory_path is None


def test_project_name_prefix_header() -> None:
    """The optional project-name prefix before CYCLE must parse."""
    text = "========== FOURSEER CYCLE 1  13:48:31Z ==========\n"
    records = parse_cycles_out(text)
    assert len(records) == 1
    assert records[0].cycle_no == 1
    assert records[0].timestamp == "13:48:31Z"
    assert records[0].outcome is None


def test_empty_input() -> None:
    """No headers -> empty list."""
    assert parse_cycles_out("") == []
    assert parse_cycles_out("just some noise\nno headers here\n") == []


def test_seed_cycles_out(seed_dir: Path) -> None:
    """Real seed: 22 cycles (7-28); 21/22/25 are wall-clock kills."""
    text = (seed_dir / "cycles.out").read_text(encoding="utf-8")
    records = parse_cycles_out(text)
    assert len(records) == 22

    by_no = {r.cycle_no: r for r in records}
    # Wall-clock-killed cycles write no OUTER lines.
    for killed in (21, 22, 25):
        assert by_no[killed].outcome is None
        assert by_no[killed].trajectory_path is None

    # Cycle 7 completed with max_steps_reached.
    assert by_no[7].outcome == "max_steps_reached"
    assert by_no[7].trajectory_path.endswith("trajectory_0013.json")
    assert by_no[7].timestamp == "16:30:45Z"
