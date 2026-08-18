"""Parse ``cycles.out`` text into :class:`~fourseer.models.CycleRecord` objects.

``cycles.out`` is the append-only stdout of the outer-loop runner. Each cycle
begins with a header line::

    ========== CYCLE 7  16:30:45Z ==========

and (for a cycle that ran to completion) is followed by two ``OUTER`` lines::

    OUTER trajectory saved to: /path/to/trajectory_0013.json
    OUTER outcome: max_steps_reached

A cycle killed by the wall-clock alarm writes NO ``OUTER`` lines at all (only a
shell "Alarm clock" line), so its ``outcome`` and ``trajectory_path`` are
``None``.

The fourseer runner prefixes the header with a project name::

    ========== FOURSEER CYCLE 1  13:48:31Z ==========

Both header forms are accepted. Parsing is pure and deterministic.
"""

from __future__ import annotations

import re

from fourseer.models import CycleRecord

__all__ = ["parse_cycles_out"]

# Header: "========== [PREFIX ]CYCLE <N>  <HH:MM:SSZ> =========="
# The optional project-name prefix (e.g. "FOURSEER ") is allowed before CYCLE.
_HEADER_RE = re.compile(
    r"^=+\s+(?:(?P<prefix>[A-Za-z0-9_-]+\s+)?)CYCLE\s+(?P<num>\d+)\s+"
    r"(?P<ts>\d{2}:\d{2}:\d{2}Z)\s+=+\s*$"
)
_TRAJ_RE = re.compile(r"^OUTER trajectory saved to:\s*(?P<path>\S+)\s*$")
_OUTCOME_RE = re.compile(r"^OUTER outcome:\s*(?P<outcome>.+?)\s*$")


def parse_cycles_out(text: str) -> list[CycleRecord]:
    """Parse *text* (the contents of a ``cycles.out`` file) into a list of
    :class:`~fourseer.models.CycleRecord`, in file order.

    Cycles that have a header but no ``OUTER`` lines (wall-clock kills) are
    still returned, with ``outcome`` and ``trajectory_path`` set to ``None``.
    """
    records: list[CycleRecord] = []
    current: CycleRecord | None = None

    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            current = CycleRecord(
                cycle_no=int(m.group("num")),
                timestamp=m.group("ts"),
                outcome=None,
                trajectory_path=None,
            )
            records.append(current)
            continue

        if current is None:
            continue

        tm = _TRAJ_RE.match(line)
        if tm:
            current = _replace(current, trajectory_path=tm.group("path"))
            records[-1] = current
            continue

        om = _OUTCOME_RE.match(line)
        if om:
            current = _replace(current, outcome=om.group("outcome"))
            records[-1] = current
            continue

    return records


def _replace(record: CycleRecord, **kwargs) -> CycleRecord:
    """Return a copy of *record* with the given fields replaced (dataclasses
    are frozen, so we rebuild)."""
    from dataclasses import replace

    return replace(record, **kwargs)
