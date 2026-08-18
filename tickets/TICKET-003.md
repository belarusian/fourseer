# TICKET-003: cycles.out parser (FIX: broken header regex)

## Title
`fourseer/parse/cycles_out.py` — `parse_cycles_out(text) -> list[CycleRecord]`.

## Evidence
`cycles.out` is the append-only stdout of the outer-loop runner. Each cycle
begins with a header `========== CYCLE 7  16:30:45Z ==========` and (for a
completed cycle) is followed by two OUTER lines:

    OUTER trajectory saved to: /path/to/trajectory_0013.json
    OUTER outcome: max_steps_reached

Wall-clock-killed cycles write NO OUTER lines (only a shell "Alarm clock"
line) — seed cycles 21, 22, 25. The seed `cycles.out` covers cycles 7-28
(22 cycles).

**BUG (blocking):** the current `_HEADER_RE` has an UNCLOSED non-capturing
group. The pattern opens `(?:` before `(?P<prefix>` but never closes it, so
`re.compile` raises `re.error: missing ), unterminated subpattern`. This breaks
the ENTIRE `fourseer` package import (top-level `__init__` -> `parse/__init__`
-> `cycles_out`). Verified: `import fourseer` fails.

## Impact
The package cannot even be imported until this regex is fixed. Every other
parser is unreachable through the public API.

## Suggestion
Fix `_HEADER_RE` so the non-capturing group is balanced. The prefix group
`(?P<prefix>[A-Za-z0-9_-]+\s+)?` must be closed with `)` before `CYCLE`.
Keep the rest of the parser: header -> new record; OUTER lines -> replace
fields; wall-clock cycles returned with `outcome`/`trajectory_path` = None.

## Tests
`tests/test_parse_cycles_out.py`:
- inline fixture with 2 completed cycles + 1 wall-clock-kill cycle (no OUTER
  lines) -> assert 3 records, kill cycle has `outcome is None`.
- assert timestamps and trajectory paths captured.
- one test against the real seed: `len == 22`, cycles 21/22/25 have
  `outcome is None`, cycle 7 outcome `max_steps_reached`.
