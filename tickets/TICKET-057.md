# TICKET-057 — gate_log: extract PR numbers + merge evidence from the launch-gate table dialect

## Problem
`fourseer taxonomy <launch-gate ai-dir>` renders `gates: -` / `merged: -` (all None)
because the launch-gate gate-log dialect is not captured by `parse_gate_log`. That
dialect uses a two-column `| Check | Result |` table whose merge-evidence row looks
like `| PR #18 | MERGED (merge commit 459f43f); branch ... deleted |`, and the gate
state lives in a `| CI (PR #18) | gate pass |` row. The current parser only reads the
seed dialect's three-column `Gate (build+test+lint)` / `Merged on main` rows and the
resume-forge `| Area | Status |` pytest row, so it never sees the launch-gate merge
evidence.

## Target
- `fourseer/parse/gate_log.py`: extend the cycle-block parser to capture, per block:
  - `pr_numbers: list[int]` — every PR number referenced in the block's Results table
    (a `| PR #N | ... |` row) and/or its `**HEAD (end):**` line (`merge of PR #N`).
  - merge evidence → set `merged = True` when a `| PR #N | MERGED ... |` row is present
    (the cell contains the word MERGED, case-insensitive). Keep the existing seed
    (`Merged on main`) and resume-forge (`**Delivery:**`) paths working.
  - gate-after enrichment for the launch-gate dialect: a `| CI (PR #N) | <status> |`
    row whose status contains `pass`/`green`/`ok` → `gate_after = "green"`; containing
    `fail`/`red` → `"red"`. Only set when not already set by an earlier dialect.
- Preserve every existing dialect (seed + resume-forge). Add a regression fixture per
  dialect touched (a committed launch-gate-dialect fragment).

## Acceptance
A launch-gate-dialect block with `| PR #18 | MERGED (merge commit 459f43f) |` yields
`merged is True`, `pr_numbers == [18]`, and a `| CI (PR #18) | gate pass |` row yields
`gate_after == "green"`. Seed + resume-forge fixtures still parse identically.
