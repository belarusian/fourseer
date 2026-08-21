"""Parse the append-only markdown gate log into a :class:`~fourseer.models.GateLog`.

The gate log is a single markdown file with two machine-relevant sections:

1. ``## Build Order`` — a markdown table with columns ``Phase | Cycles | Target``.
   Each data row becomes a :class:`~fourseer.models.BuildOrderRow`.

2. ``## Cycle N`` — one block per executed cycle. The header is
   ``## Cycle N: <title>`` (the title may be absent, e.g. ``## Cycle 1 — Pending``).
   The body carries optional ``**Date:**``, ``**HEAD (start):**`` and
   ``**HEAD (end):**`` fields, an optional ``### Results`` markdown table, and an
   optional ``### Lessons`` numbered list. Each block becomes a
   :class:`~fourseer.models.CycleBlock`.

From the ``### Results`` table the parser captures two rows when present: the
``Gate (build+test+lint)`` row's ``After`` cell (lowercased to ``"green"`` /
``"red"``) and the ``Merged on main`` row's ``After`` cell (``True`` when it
carries a commit hash / PR reference, ``False`` when it is an em-dash or empty).
A block with no ``### Results`` table leaves both ``None``.

Alternate block dialects are also accepted: a ``**Lessons:**`` line (with
numbered or ``-`` bullet items) stands in for ``### Lessons``; a two-column
``| Area | Status |`` gate table without a ``### Results`` header contributes
its pytest row to ``gate_after``; and a ``**Delivery:**`` line naming a merge
into ``main`` sets ``merged`` to ``True``.

Parsing is pure and deterministic. The remaining free-form prose (``### What We
Did``) is ignored.
"""

from __future__ import annotations

import re

from fourseer.models import BuildOrderRow, CycleBlock, GateLog

__all__ = ["parse_gate_log"]

# "## Cycle 3: Foundations — ..." or "## Cycle 1 — Pending"
_CYCLE_HEADER_RE = re.compile(r"^##\s+Cycle\s+(?P<num>\d+)\b\s*(?P<rest>.*)$")
_DATE_RE = re.compile(r"^\*\*Date:\*\*\s*(?P<val>.+?)\s*$")
_HEAD_START_RE = re.compile(r"^\*\*HEAD \(start\):\*\*\s*(?P<val>.+?)\s*$")
_HEAD_END_RE = re.compile(r"^\*\*HEAD \(end\):\*\*\s*(?P<val>.+?)\s*$")
_LESSONS_HEADER_RE = re.compile(r"^(?:###\s+Lessons\b|\*\*Lessons:?\*\*)")
_LESSON_ITEM_RE = re.compile(r"^\s*(?:\d+\.|-)\s+(?P<val>.+?)\s*$")
_RESULTS_HEADER_RE = re.compile(r"^###\s+Results\b")
_BUILD_ORDER_HEADER_RE = re.compile(r"^##\s+Build Order\b")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_DELIVERY_RE = re.compile(r"""^\*\*Delivery:.*->\s*[`'"]?main\b""")

# A "Merged on main" After cell that is one of these means "not merged".
_MERGED_ABSENT = {"", "—", "–", "-"}


def parse_gate_log(text: str) -> GateLog:
    """Parse *text* (the contents of a gate-log markdown file) into a
    :class:`~fourseer.models.GateLog`.

    Returns a ``GateLog`` whose ``build_order`` holds the Build Order table rows
    and whose ``cycles`` holds every ``## Cycle N`` block, both in file order.
    """
    lines = text.splitlines()
    build_order = _parse_build_order(lines)
    cycles = _parse_cycle_blocks(lines)
    return GateLog(build_order=build_order, cycles=cycles)


def _parse_build_order(lines: list[str]) -> list[BuildOrderRow]:
    """Extract the ``## Build Order`` markdown table rows."""
    rows: list[BuildOrderRow] = []
    in_table = False
    for line in lines:
        if _BUILD_ORDER_HEADER_RE.match(line):
            in_table = True
            continue
        if in_table:
            # A new "## " section ends the table.
            if line.startswith("## "):
                break
            row_match = _TABLE_ROW_RE.match(line)
            if row_match is None:
                continue
            if _TABLE_SEP_RE.match(line):
                continue
            cells = [c.strip() for c in row_match.group(1).split("|")]
            # Skip the header row (Phase | Cycles | Target).
            if len(cells) < 3 or cells[0].lower() == "phase":
                continue
            rows.append(BuildOrderRow(phase=cells[0], cycles=cells[1], target=cells[2]))
    return rows


def _parse_merged_cell(after: str) -> bool:
    """Interpret a ``Merged on main`` ``After`` cell as a merge flag.

    ``True`` when the cell carries a commit hash / PR reference (any non-empty
    value that is not an em-dash / hyphen placeholder); ``False`` when it is an
    em-dash, hyphen, or empty.
    """
    return after.strip() not in _MERGED_ABSENT


def _parse_cycle_blocks(lines: list[str]) -> list[CycleBlock]:
    """Extract every ``## Cycle N`` block with its structured fields.

    A mutable dict accumulator is used while scanning (the model is frozen),
    and a :class:`CycleBlock` is materialized when the next block begins or at
    end of input. The ``### Results`` table's ``Gate (build+test+lint)`` and
    ``Merged on main`` rows are captured into ``gate_after`` / ``merged``.
    """
    blocks: list[CycleBlock] = []
    current: dict | None = None
    in_lessons = False
    in_results = False

    def _flush() -> None:
        nonlocal current
        if current is not None:
            blocks.append(
                CycleBlock(
                    cycle_no=current["cycle_no"],
                    title=current["title"],
                    date=current["date"],
                    head_start=current["head_start"],
                    head_end=current["head_end"],
                    lessons=current["lessons"],
                    gate_after=current["gate_after"],
                    merged=current["merged"],
                )
            )
            current = None

    for line in lines:
        m = _CYCLE_HEADER_RE.match(line)
        if m:
            _flush()
            rest = m.group("rest").strip()
            # Title is the text after a leading colon, else the raw rest.
            title = rest[1:].strip() if rest.startswith(":") else rest
            current = {
                "cycle_no": int(m.group("num")),
                "title": title,
                "date": None,
                "head_start": None,
                "head_end": None,
                "lessons": [],
                "gate_after": None,
                "merged": None,
            }
            in_lessons = False
            in_results = False
            continue

        if current is None:
            continue

        if _LESSONS_HEADER_RE.match(line):
            in_lessons = True
            in_results = False
            continue

        if _RESULTS_HEADER_RE.match(line):
            in_results = True
            in_lessons = False
            continue

        if in_lessons:
            lm = _LESSON_ITEM_RE.match(line)
            if lm:
                current["lessons"].append(lm.group("val"))
                continue
            if line.strip() == "":
                continue
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("|"):
                # A new section header or table row ends the lessons list.
                in_lessons = False
            elif current["lessons"]:
                # Continuation of the most recent numbered lesson.
                current["lessons"][-1] = current["lessons"][-1] + " " + stripped
                continue
            else:
                # A non-item, non-blank line before any lesson ends the section.
                in_lessons = False

        if in_results:
            # A new "### " section header (other than Results) ends the table.
            if line.startswith("###"):
                in_results = False
                continue
            row_match = _TABLE_ROW_RE.match(line)
            if row_match is not None and not _TABLE_SEP_RE.match(line):
                cells = [c.strip() for c in row_match.group(1).split("|")]
                if len(cells) >= 3:
                    label = cells[0].lower()
                    after = cells[2]
                    if label == "gate (build+test+lint)":
                        low = after.lower()
                        if low in ("green", "red"):
                            current["gate_after"] = low
                    elif label == "merged on main":
                        current["merged"] = _parse_merged_cell(after)
            continue

        if not in_lessons:
            dm = _DATE_RE.match(line)
            if dm:
                current["date"] = dm.group("val")
                continue
            hsm = _HEAD_START_RE.match(line)
            if hsm:
                current["head_start"] = hsm.group("val")
                continue
            hem = _HEAD_END_RE.match(line)
            if hem:
                current["head_end"] = hem.group("val")
                continue
            if _DELIVERY_RE.match(line):
                current["merged"] = True
                continue
            tmm = _TABLE_ROW_RE.match(line)
            if tmm is not None and not _TABLE_SEP_RE.match(line):
                cells = [c.strip() for c in tmm.group(1).split("|")]
                if len(cells) == 2:
                    label = cells[0].lower()
                    status = cells[1].lower()
                    if "pytest" in label or "build+test" in label or label == "gate":
                        if "fail" in status:
                            current["gate_after"] = "red"
                        else:
                            current["gate_after"] = (
                                "green"
                                if any(
                                    k in status for k in ("passed", "green", "ok")
                                )
                                else "red"
                            )
                continue

    _flush()
    return blocks
