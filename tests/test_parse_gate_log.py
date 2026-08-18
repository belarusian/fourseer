"""Tests for :func:`fourseer.parse.gate_log.parse_gate_log`.

Covers the multi-line-lesson fix (TICKET-004): a numbered lesson that wraps
across several lines must be accumulated in full, not truncated to its first
line. Uses small inline fixtures plus one test against the real seed dataset.
"""

from __future__ import annotations

from pathlib import Path

from fourseer.parse.gate_log import parse_gate_log

# Build Order table (2 rows) + two cycle blocks. Cycle 2 has a multi-line
# lesson (item 1 wraps across two lines) and a second single-line lesson.
FIXTURE = """\
## Build Order
| Phase | Cycles | Target |
|---|---|---|
| Foundations | 1-3 | Session append-only log |
| LLM seam | 4-6 | llm-adapter as a plain module |

## Cycles

## Cycle 1 — Pending

## Cycle 2: Foundations — harden the session log
**Date:** 2026-08-17
**HEAD (start):** e021337 (main)
**HEAD (end):** 8312b08 (main)

### What We Did
Some prose that should be ignored.

### Lessons
1. **Trust SCAN over the briefing.** The briefing was a stale snapshot, so
   always re-verify on-disk state before acting.
2. **Scope the auditor to our repo.** Pointing it at the seed path audits the
   wrong repo.

### Results
| Check | Before | After |
|---|---|---|
| build | red | green |
"""


def test_build_order_rows() -> None:
    """The Build Order table yields one row per data row, header skipped."""
    gl = parse_gate_log(FIXTURE)
    assert len(gl.build_order) == 2
    assert gl.build_order[0].phase == "Foundations"
    assert gl.build_order[0].cycles == "1-3"
    assert gl.build_order[0].target == "Session append-only log"
    assert gl.build_order[1].phase == "LLM seam"
    assert gl.build_order[1].cycles == "4-6"


def test_cycle_fields() -> None:
    """Cycle 2 carries date, head start/end, and its title."""
    gl = parse_gate_log(FIXTURE)
    c2 = next(c for c in gl.cycles if c.cycle_no == 2)
    assert c2.title == "Foundations — harden the session log"
    assert c2.date == "2026-08-17"
    assert c2.head_start == "e021337 (main)"
    assert c2.head_end == "8312b08 (main)"


def test_multiline_lesson_accumulated() -> None:
    """A wrapped numbered lesson is captured in full, not truncated."""
    gl = parse_gate_log(FIXTURE)
    c2 = next(c for c in gl.cycles if c.cycle_no == 2)
    assert len(c2.lessons) == 2
    # Lesson 1 spans two source lines; both must be present.
    assert c2.lessons[0].startswith("**Trust SCAN over the briefing.**")
    assert "always re-verify on-disk state before acting." in c2.lessons[0]
    # Lesson 2 is a single line.
    assert c2.lessons[1] == "**Scope the auditor to our repo.** Pointing it at the seed path audits the wrong repo."


def test_pending_cycle_has_no_fields() -> None:
    """A '## Cycle N — Pending' block has no date/head/lessons."""
    gl = parse_gate_log(FIXTURE)
    c1 = next(c for c in gl.cycles if c.cycle_no == 1)
    assert c1.title == "— Pending"
    assert c1.date is None
    assert c1.head_start is None
    assert c1.head_end is None
    assert c1.lessons == []


def test_seed_gate_log(seed_dir: Path) -> None:
    """Real seed: 6 build-order rows, 26 cycle blocks, cycle 3 has 3 full lessons."""
    text = (seed_dir / "gate-log.md").read_text(encoding="utf-8")
    gl = parse_gate_log(text)
    assert len(gl.build_order) == 6
    assert len(gl.cycles) == 26

    c3 = next(c for c in gl.cycles if c.cycle_no == 3)
    assert len(c3.lessons) == 3
    # The first lesson is multi-line; it must contain the full first sentence
    # (not just "Trust SCAN over the briefing.").
    assert c3.lessons[0].startswith("**Trust SCAN over the briefing.**")
    assert "source of truth" in c3.lessons[0]
