# TICKET-041: `detect_issue_drift` in drift.py

## Title
Add `detect_issue_drift(commits, open_issues) -> list[IssueDrift]` to
`fourseer/drift.py` — the closed-in-commits-but-still-open intersection.

## Evidence
`fourseer/drift.py` does not exist. The core drift signal is the set of issues
referenced-as-closed in commit messages that are ALSO still open.

## Impact
Without it, fourseer cannot surface the issue-drift diff the Build Order
promises (cycle 9).

## Suggestion
In `fourseer/drift.py`, add `detect_issue_drift(commits: list[CommitRecord],
open_issues: set[int]) -> list[IssueDrift]`. Return one `IssueDrift` per issue
that is BOTH referenced by some commit subject AND in `open_issues`; dedupe to
one row per issue using the FIRST referencing commit in `commits` order; sort by
`issue_no`. Return `[]` when there is no drift (empty `open_issues`, no
references, or no overlap). Pure, deterministic, stdlib-only, no I/O, no mutation.
