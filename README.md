# fourseer

Loop intelligence for the four pipeline. A stdlib-first Python CLI + library
that parses autonomous-build loop artifacts (trajectories JSON, append-only
markdown gate log, `cycles.out`, git history) and reports:

- **report** — per-cycle metrics: duration, outcome class, steps, tokens/cost
- **taxonomy** — failure-mode classes: wall-clock-kill, max_steps, red-gate,
  incomplete-vs-merged
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
  count, mode counts, gate counts, and merged counts.
- `fourseer drift <ai-dir>` — plan drift: the Build Order plan compared
  against the cycles actually executed (`planned_not_executed` /
  `executed_not_planned`).

Exit-code contract: `0` on success; `2` when `<ai-dir>` is missing or not a
directory (a short error is printed to stderr, stdout is empty).

Note: `drift` is *plan* drift only. Issue drift requires a caller-supplied set
of still-open issue numbers (e.g. from `gh issue list`) that is not derivable
from any artifact on disk, so it is a library function
(`fourseer.drift.detect_issue_drift`), not a default subcommand.
