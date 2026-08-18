# TICKET-005: git history reader + full test suite + gate

## Title
`fourseer/parse/git_history.py` — `read_git_history(repo_path) -> list[CommitRecord]`,
plus the complete test suite and a green gate.

## Evidence
Duration metrics (report cycle) need commit timestamps. `git log` with a fixed,
unambiguous format string is the stdlib-only way to read them. The current
implementation uses `%H\x1f%h\x1f%an\x1f%ad\x1f%s` with `--date=iso` and
splits on the unit-separator byte — this is robust against subjects containing
`|`. Verified against the fourseer repo: returns 1 commit with correct
hash/short/author/date/subject.

However, NO tests exist for any parser yet, and the package does not even
import (TICKET-003 regex bug). The gate (`pytest tests/ -x -q` +
`ruff check fourseer/` + `mypy fourseer/ --ignore-missing-imports`) is currently
red.

## Impact
A cycle is not complete until the code is merged on main with a green gate.
Without tests, the parsers (and the two bug fixes in TICKET-003/004) are
unverified and the merge is blocked.

## Suggestion
- Keep `read_git_history` as-is (it works); ensure it raises `FileNotFoundError`
  for a missing path and `RuntimeError` when `git log` fails.
- Add the full test suite: `tests/test_models.py`,
  `tests/test_parse_trajectories.py`, `tests/test_parse_cycles_out.py`,
  `tests/test_parse_gate_log.py`, `tests/test_parse_git_history.py`. Each parser
  gets focused inline-fixture tests PLUS one test against the real seed dataset
  (`/home/sasha/AI/fourseer/seed`).
- Run the gate: `pytest tests/ -x -q`, `ruff check fourseer/`,
  `mypy fourseer/ --ignore-missing-imports`. All must pass before merge.

## Tests
`tests/test_parse_git_history.py`:
- against the fourseer repo itself: at least 1 record, fields populated,
  `short_hash` is a prefix of `hash`.
- a temp git repo (created via subprocess in the test) with 2 commits ->
  assert 2 records in newest-first order.
- a non-existent path -> `FileNotFoundError`.
