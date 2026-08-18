# TICKET-042: `render_issue_drift` in drift.py

## Title
Add `render_issue_drift(drift) -> str` to `fourseer/drift.py` — a deterministic
human-readable block for the issue-drift diff.

## Evidence
`fourseer/drift.py` does not exist. The other phases (report / taxonomy) each
have a renderer (`render_report` / `render_summary` / `render_taxonomy`); drift
needs one for style consistency.

## Impact
Without it, the drift diff has no human-readable form for the CLI (cycle 11-12).

## Suggestion
In `fourseer/drift.py`, add `render_issue_drift(drift: list[IssueDrift]) -> str`,
consistent in style with `render_summary` / `render_taxonomy`: a header line
`# Issue Drift (N issues)` and one line per drifted issue (in `issue_no` order),
or a single stable no-drift line when empty. Always ends with a trailing
newline. Pure, deterministic, stdlib-only, no I/O, no mutation.
