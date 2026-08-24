# TICKET-061 — tests + README: dialect regression, lost-vs-landed taxonomy test, E2E, honest docs

## Problem
No tests pin the launch-gate dialect or the lost-vs-landed distinction, and the README
taxonomy blurb overclaims "incomplete-vs-merged" without documenting the landed/lost
dimension or the supported gate-log dialects.

## Target
- `tests/test_parse_gate_log_dialect.py` (or a new file): unit tests per dialect variant
  (seed, resume-forge, launch-gate) asserting `pr_numbers`, `merged`, and `gate_after`.
- `tests/test_taxonomy.py`: a test asserting lost-vs-landed on the committed golden
  fixture (cycle-2 shape → `lost`, cycle-5 shape → `landed`), plus the landed/lost
  distribution + render line.
- `tests/test_cli_e2e.py` (or new): an E2E `fourseer taxonomy` run against the fixture
  dir asserting the `landed:` line and that gates:/merged: are populated (not `-`).
- `README.md`: document the landed/lost dimension and the supported gate-log dialects
  honestly; correct the overclaiming "incomplete-vs-merged" blurb to match the code.

## Acceptance
Full suite green (`pytest tests/ -x -q`, `ruff check fourseer/`,
`mypy fourseer/ --ignore-missing-imports`). E2E against the fixture dir reports cycle 2
as lost and cycle 5 as landed with populated gates:/merged:. README matches the code.
