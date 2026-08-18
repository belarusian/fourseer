# TICKET-043: Re-exports + focused tests + one real-history test

## Title
Re-export the four drift symbols from `fourseer/__init__.py` and add a focused
test suite (`tests/test_drift.py`) with exactly one real-history test.

## Evidence
`fourseer/__init__.py` does not export any drift symbols; `tests/test_drift.py`
does not exist. The drift module needs a public surface and test coverage.

## Impact
Without re-exports the drift API is not part of the package surface; without
tests the parsing/detection/rendering semantics are unpinned.

## Suggestion
In `fourseer/__init__.py`, re-export `IssueDrift` (under `# models`) and
`extract_closed_issues` / `detect_issue_drift` / `render_issue_drift` (under a
new `# drift` group); add all four to `__all__`. In `tests/test_drift.py`, add
focused inline-fixture unit tests (hand-built `CommitRecord` lists / `set[int]`
open sets — NOT the full seed) for every function plus the `IssueDrift` value
object (frozen / hashable / `code` default). Add exactly ONE real-history test
gated on the `seed_dir` fixture (skips when the seed is absent) that reads the
FOURSEER REPO'S OWN history via `read_git_history(<repo root>)` (the seed has no
`.git`), asserts `extract_closed_issues` yields a non-empty stable set of
referenced issue numbers (pin the stable subset from the merge commits) and that
`detect_issue_drift(commits, set()) == []`.
