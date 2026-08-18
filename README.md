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