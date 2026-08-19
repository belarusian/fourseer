"""fourseer — loop intelligence for the four pipeline.

A stdlib-first Python CLI + library that parses autonomous-build loop
artifacts (trajectories JSON, append-only markdown gate log, cycles.out,
git history) and reports per-cycle metrics, a failure-mode taxonomy, and
drift (issue drift + plan drift).

Public surface is re-exported here; submodules:
  - fourseer.models   : typed dataclasses for the parsed artifacts
  - fourseer.parse    : artifact parsers (trajectories, cycles.out, gate log, git)
  - fourseer.load     : top-level loader (composes the four parsers into a Run)
  - fourseer.validate : cross-source consistency validation (validate_run)
  - fourseer.report   : per-cycle metrics + report renderer + tokens/cost
                        + run-level summary (summarize_run / render_summary)
  - fourseer.taxonomy : failure-mode classification + run-level distribution
                        summary (summarize_taxonomy / render_taxonomy)
  - fourseer.drift    : issue + plan drift detection
  - fourseer.cli      : the `fourseer` entrypoint
"""

from fourseer.drift import (
    detect_issue_drift,
    detect_plan_drift,
    extract_closed_issues,
    planned_cycle_set,
    render_issue_drift,
    render_plan_drift,
)
from fourseer.load import load_run
from fourseer.models import (
    BuildOrderRow,
    CommitRecord,
    ConsistencyIssue,
    CycleBlock,
    CycleClassification,
    CycleMetrics,
    CycleRecord,
    GateLog,
    IssueDrift,
    PlanDrift,
    Run,
    RunSummary,
    TaxonomySummary,
    Trajectory,
)
from fourseer.parse import (
    load_trajectories,
    parse_cycles_out,
    parse_gate_log,
    read_git_history,
)
from fourseer.report import (
    build_cycle_metrics,
    extract_tokens_cost,
    render_report,
    render_summary,
    summarize_run,
)
from fourseer.taxonomy import classify_cycle, classify_run, render_taxonomy, summarize_taxonomy
from fourseer.validate import validate_run

__version__ = "1.0.0"
__all__ = [
    "__version__",
    # models
    "Trajectory",
    "CycleRecord",
    "CycleMetrics",
    "BuildOrderRow",
    "CycleBlock",
    "CycleClassification",
    "GateLog",
    "CommitRecord",
    "Run",
    "ConsistencyIssue",
    "RunSummary",
    "TaxonomySummary",
    "IssueDrift",
    "PlanDrift",
    # loaders
    "load_run",
    # report
    "build_cycle_metrics",
    "render_report",
    "extract_tokens_cost",
    "summarize_run",
    "render_summary",
    # validation
    "validate_run",
    # taxonomy
    "classify_cycle",
    "classify_run",
    "summarize_taxonomy",
    "render_taxonomy",
    # drift
    "extract_closed_issues",
    "detect_issue_drift",
    "render_issue_drift",
    "planned_cycle_set",
    "detect_plan_drift",
    "render_plan_drift",
    # parsers
    "load_trajectories",
    "parse_cycles_out",
    "parse_gate_log",
    "read_git_history",
]
