"""fourseer — loop intelligence for the four pipeline.

A stdlib-first Python CLI + library that parses autonomous-build loop
artifacts (trajectories JSON, append-only markdown gate log, cycles.out,
git history) and reports per-cycle metrics, a failure-mode taxonomy, and
drift (issue drift + plan drift).

Public surface is re-exported here; submodules:
  - fourseer.models   : typed dataclasses for the parsed artifacts
  - fourseer.parse    : artifact parsers (trajectories, cycles.out, gate log, git)
  - fourseer.load     : top-level loader (composes the four parsers into a Run)
  - fourseer.report   : per-cycle metrics
  - fourseer.taxonomy : failure-mode classification
  - fourseer.drift    : issue + plan drift detection
  - fourseer.cli      : the `fourseer` entrypoint
"""

from fourseer.load import load_run
from fourseer.models import (
    BuildOrderRow,
    CommitRecord,
    CycleBlock,
    CycleRecord,
    GateLog,
    Run,
    Trajectory,
)
from fourseer.parse import (
    load_trajectories,
    parse_cycles_out,
    parse_gate_log,
    read_git_history,
)

__version__ = "0.1.0"
__all__ = [
    "__version__",
    # models
    "Trajectory",
    "CycleRecord",
    "BuildOrderRow",
    "CycleBlock",
    "GateLog",
    "CommitRecord",
    "Run",
    # loaders
    "load_run",
    # parsers
    "load_trajectories",
    "parse_cycles_out",
    "parse_gate_log",
    "read_git_history",
]
