"""Tests for the alternate gate-log dialect used by resume-forge logs.

Some gate logs do not use the ``### Lessons`` / ``### Results`` anchors.
They instead carry:

- a ``**Lessons:**`` line followed by ``-`` bullet items (with wrapped
  continuation lines),
- a two-column ``| Area | Status |`` gate table with no ``### Results``
  header, whose pytest row encodes the gate state, and
- a ``**Delivery:**`` line naming a merge into ``main``.

These tests pin parser support for that dialect so a log of this shape
cannot silently regress to ``0 cycles`` / ``merged=None`` /
``gate_after=None``.
"""

from __future__ import annotations

from fourseer.parse.gate_log import parse_gate_log

DIALECT_FIXTURE = """\
## Build Order
| Phase | Cycles | Target |
|---|---|---|
| mine | 3-5 | GitHub history mining |
| render | 11-12 | HTML + PDF output |

## Cycles

## Cycle 1 — Pending

## Cycle 12 — Consolidation/hardening: e2e integration test, docs, v0.1.0 tag
**Date:** 2026-08-20
**HEAD (start):** 830048d (Cycle 11 merge on main)
**HEAD (end):** 7df02d0 (PR #60 follow-up squash-merge on main)

**What We Did:**
- Final cycle of the Build Order.
- End-to-end offline integration test and docs rewrite.

**Delivery:** Delivered via **PR #59** (build12/consolidation -> main).
Single squashed commit 7e852f4; source branch deleted.

| Area | Status |
|---|---|
| pytest tests/ -x -q | 224 passed (216 prior + 8 new) |
| ruff check resume_forge/ | All checks passed! |
| mypy resume_forge/ | Success: no issues found in 11 source files |

**Lessons:**
- The outer two-phase disk check caught a ruff slip the inner missed;
  trust the gate re-run over the inner done claim.
- A second lesson that is a single line.
"""

RED_FIXTURE = """\
## Cycle 13 — Broken experiment
**Date:** 2026-08-21

**Delivery:** Delivered via **PR #70** (build13/broken -> staging).

| Area | Status |
|---|---|
| pytest tests/ -x -q | 3 failed, 221 passed |
"""


def test_dialect_lessons_parsed() -> None:
    """A **Lessons:** bullet list parses, including wrapped items."""
    gl = parse_gate_log(DIALECT_FIXTURE)
    blocks = {b.cycle_no: b for b in gl.cycles}
    lessons = blocks[12].lessons
    assert len(lessons) == 2
    assert lessons[0].startswith("The outer two-phase disk check caught")
    assert "trust the gate re-run" in lessons[0]
    assert lessons[1] == "A second lesson that is a single line."


def test_dialect_gate_after_from_two_column_table() -> None:
    """A headerless | Area | Status | pytest row drives gate_after to green."""
    gl = parse_gate_log(DIALECT_FIXTURE)
    blocks = {b.cycle_no: b for b in gl.cycles}
    assert blocks[12].gate_after == "green"


def test_dialect_gate_after_red() -> None:
    """A failing pytest row drives gate_after to red."""
    gl = parse_gate_log(RED_FIXTURE)
    assert gl.cycles[0].gate_after == "red"


def test_dialect_delivery_sets_merged() -> None:
    """A **Delivery:** line into main marks the block merged."""
    gl = parse_gate_log(DIALECT_FIXTURE)
    blocks = {b.cycle_no: b for b in gl.cycles}
    assert blocks[12].merged is True
    assert blocks[1].merged is None


def test_dialect_head_and_dates_still_parsed() -> None:
    """Date and HEAD fields parse unchanged under the new dialect."""
    gl = parse_gate_log(DIALECT_FIXTURE)
    blocks = {b.cycle_no: b for b in gl.cycles}
    assert blocks[12].date == "2026-08-20"
    assert blocks[12].head_start == "830048d (Cycle 11 merge on main)"
    assert blocks[12].head_end == "7df02d0 (PR #60 follow-up squash-merge on main)"
    assert gl.build_order[0].phase == "mine"
