# fourseer

Loop intelligence for the four pipeline. A stdlib-first Python CLI + library
that parses autonomous-build loop artifacts (trajectories JSON, append-only
markdown gate log, `cycles.out`, git history) and reports:

- **report** — per-cycle metrics: duration, outcome class, steps, tokens/cost
- **taxonomy** — failure-mode classes (mode): wall-clock-kill, max_steps,
  task-complete; plus orthogonal per-cycle dimensions for gate state, merge
  evidence, and landed-vs-lost work
- **drift** — issue drift (closed-in-commits-but-still-open) and plan drift
  (Build Order plan vs cycles executed)

## Usage

Install (dev): `pip install -e ".[dev]"`. Each subcommand takes one positional
argument, `<ai-dir>` — the project AI-artifact directory containing
`cycles.out`, `gate-log.md`, and `trajectories/`.

Run via the console script or the module form (identical behavior):

    fourseer <subcommand> <ai-dir>
    python -m fourseer <subcommand> <ai-dir>

- `fourseer report <ai-dir>` — per-cycle metrics table (duration, outcome
  class, steps, trajectory) for every cycle in the run.
- `fourseer taxonomy <ai-dir>` — run-level failure-mode distribution: cycle
  count, mode counts, gate counts, merged counts, and the landed-vs-lost
  dimension (how many cycles landed their work vs lost it).
- `fourseer drift <ai-dir>` — plan drift: the Build Order plan compared
  against the cycles actually executed (`planned_not_executed` /
  `executed_not_planned`).

Exit-code contract: `0` on success; `2` when `<ai-dir>` is missing or not a
directory (a short error is printed to stderr, stdout is empty).

Note: `drift` is *plan* drift only. Issue drift requires a caller-supplied set
of still-open issue numbers (e.g. from `gh issue list`) that is not derivable
from any artifact on disk, so it is a library function
(`fourseer.drift.detect_issue_drift`), not a default subcommand.

## The landed-vs-lost dimension

`mode` is a closed set derived from a cycle's outcome string, so two wall-clock
kills that share `outcome is None` are indistinguishable by mode alone — even
when one **landed** its work (merged a PR before the wall) and the other
**lost** it (killed with nothing merged). fourseer therefore tracks an
orthogonal per-cycle dimension, `landed`, in addition to `mode`:

- **`landed`** — the cycle's gate-log block exists *and* carries merge evidence
  (`merged is True`);
- **`lost`** — the cycle ran (it appears in `cycles.out`) but has no gate-log
  block, or its block carries no merge evidence;
- **`unknown`** — a block exists but the merge evidence is ambiguous
  (`merged is None`).

The dimension is derived purely and deterministically from the artifacts and
never affects `mode`. The run-level summary tallies it into `landed_counts` /
`landed_unknown` (invariant: `sum(landed_counts.values()) + landed_unknown ==
cycle_count`) and `fourseer taxonomy` renders a `landed:` line; `fourseer
report` adds a trailing `Landed` column to the per-cycle table.

## Supported gate-log dialects

The gate-log parser (`fourseer.parse.gate_log`) recognizes the cycle-block
dialects produced by the four pipeline's runners and extracts, per block, the
PR numbers referenced, merge evidence, and post-gate state:

- **seed** — a three-column `### Results` table with `Gate (build+test+lint)`
  and `Merged on main` rows.
- **resume-forge** — a `| Area | Status |` table (the pytest row feeds
  `gate_after`) plus a `**Delivery:**` line naming the merge.
- **launch-gate** — a two-column `| Check | Result |` table whose merge-evidence
  row looks like `| PR #18 | MERGED (merge commit …); branch … deleted |` and
  whose gate state lives in a `| CI (PR #18) | gate pass |` row. A `MERGED`
  cell sets `merged = True`; the `CI (PR #N)` status maps to `gate_after`.

All three dialects are pinned by committed fixtures under `tests/fixtures/`
(`dialect_seed.md`, `dialect_resume_forge.md`, `dialect_launch_gate.md`, and
the full `launch_gate/` golden run) and covered by unit tests in
`tests/test_parse_gate_log_dialect.py`.
