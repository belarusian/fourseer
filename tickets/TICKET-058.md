# TICKET-058 — models + taxonomy: the landed/lost dimension (orthogonal to mode)

## Problem
`mode` is a closed set derived from the outcome string, so two wall-clock kills that
share `outcome is None` are indistinguishable even when one LOST its work and the other
LANDED it. On the launch-gate run, cycle 2 (killed at the wall; no gate-log block; no
merged PR) and cycle 5 (killed at the wall AFTER the inner merged PR #18 and appended a
`## Cycle 5` block) both classify as `mode == "wall_clock_kill"` — fourseer cannot tell
them apart.

## Target
- `fourseer/models.py`: add a backward-compatible trailing field to
  `CycleClassification`, `landed: str | None = None`, with a closed set of values
  documented in the docstring: `"landed"`, `"lost"`, `"unknown"`. Keep `mode` outcome-
  derived and stable (the closed mode set is unchanged).
- `fourseer/taxonomy.py`: derive `landed` in `classify_cycle` / `classify_run`:
  - a cycle is **landed** when its gate-log block exists AND carries merge evidence
    (`merged is True`);
  - a cycle is **lost** when it ran (it is in the `cycles.out` metrics) but has NO
    gate-log block, OR its block carries no merge evidence;
  - a cycle is **unknown** when evidence is incomplete (e.g. a block exists with merge
    evidence ambiguous / `merged is None` while a block is present).
  The derivation must be pure, deterministic, stdlib-only, and never affect `mode`.

## Acceptance
On the launch-gate run: cycle 2 → `landed == "lost"`; cycle 5 → `landed == "landed"`.
Both keep `mode == "wall_clock_kill"`. A completed (non-kill) cycle with a merged block
is `landed`; a kill with no block is `lost`.
