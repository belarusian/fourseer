# TICKET-040: `extract_closed_issues` in drift.py

## Title
Add `extract_closed_issues(commits) -> list[tuple[int, str, str]]` to a new
`fourseer/drift.py` module that parses commit subjects for issue references.

## Evidence
`fourseer/drift.py` does not exist. The Drift phase needs to turn a
`list[CommitRecord]` (from `read_git_history`) into the set of issue numbers
each commit references, so it can be cross-checked against a still-open set.

## Impact
Without it, issue drift cannot be computed: there is no way to derive the
referenced issue numbers from commit messages.

## Suggestion
In `fourseer/drift.py`, add `extract_closed_issues(commits) ->
list[tuple[int, str, str]]` (issue_no, commit_hash, commit_message). Match
issue references case-insensitively: the keywords `Closes`/`Fixes`/`Resolves`/
`Refs`/`See` followed by `#<int>`, plus a bare `#<int>` anywhere (a conservative
superset — document the choice). Dedupe per commit (same issue twice → once) and
return a stable list sorted by `issue_no` (ties broken by commit position). Pure,
deterministic, stdlib-only (regex), no I/O, no mutation.
