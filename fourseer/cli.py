"""The ``fourseer`` command-line entrypoint.

This module is the thin I/O boundary of the library. It wires the existing
pure functions (``load_run`` + the ``build_*`` / ``classify_*`` / ``detect_*``
+ ``render_*`` family) into three subcommands, each taking a single positional
``<project-ai-dir>`` and printing the corresponding human-readable block to
stdout:

- ``fourseer report <ai-dir>``   -> ``render_report(build_cycle_metrics(run))``
- ``fourseer taxonomy <ai-dir>`` -> ``render_taxonomy(summarize_taxonomy(classify_run(run)))``
- ``fourseer drift <ai-dir>``    -> ``render_plan_drift(detect_plan_drift(run.gate_log, executed))``

The CLI does NO parsing or aggregation itself: every subcommand is a thin
composition of the existing library functions. It is deterministic (the same
AI directory always yields the same stdout for a given subcommand) and
stdlib-only (``argparse``, ``sys``, ``pathlib``).

Why ``drift`` is *plan* drift only
----------------------------------
Plan drift is self-contained: it compares the Build Order table (planned
cycles) against the cycles actually executed (from ``cycles.out``), both of
which the loader reads. Issue drift, by contrast, needs a *caller-supplied*
set of still-open issue numbers (in a real deployment, from ``gh issue list``)
that is not derivable from any artifact on disk. Because that input has no
default source, issue drift is deliberately NOT a default subcommand; it
remains available as the library function
:func:`fourseer.drift.detect_issue_drift` for callers that can supply the open
set.

Error handling
--------------
``main`` returns ``0`` on success. When the AI directory is missing or not a
directory it prints a short error to stderr and returns ``2`` (it never raises
an uncaught exception for a missing dir). Usage errors (no subcommand, missing
argument) are handled by ``argparse`` itself.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fourseer.drift import detect_plan_drift, render_plan_drift
from fourseer.load import load_run
from fourseer.report import build_cycle_metrics, render_report
from fourseer.taxonomy import classify_run, render_taxonomy, summarize_taxonomy

__all__ = ["main"]

# Exit code for a missing / unreadable AI directory (distinct from argparse's
# usage-error code, which is also 2, but produced by a different code path).
_MISSING_DIR_EXIT = 2


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level ``fourseer`` parser with its three subcommands."""
    parser = argparse.ArgumentParser(
        prog="fourseer",
        description="Loop intelligence for the four pipeline: parse, report, taxonomy, drift.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="per-cycle metrics table")
    p_report.add_argument("ai_dir", help="path to the project AI-artifact directory")

    p_taxonomy = sub.add_parser("taxonomy", help="failure-mode distribution")
    p_taxonomy.add_argument("ai_dir", help="path to the project AI-artifact directory")

    p_drift = sub.add_parser("drift", help="plan drift (Build Order vs executed cycles)")
    p_drift.add_argument("ai_dir", help="path to the project AI-artifact directory")

    return parser


def _emit(text: str) -> None:
    """Write a rendered block to stdout, preserving its exact trailing newline.

    The ``render_*`` functions already end with a single trailing newline, so
    this writes the string verbatim (no extra newline) to keep the output
    deterministic and byte-stable.
    """
    sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    """Run the ``fourseer`` CLI.

    Parameters
    ----------
    argv:
        The argument list (without the program name). ``None`` means use
        ``sys.argv[1:]``.

    Returns
    -------
    int
        ``0`` on success; ``2`` when the AI directory is missing or not a
        directory (a short error is printed to stderr). Usage errors are
        handled by ``argparse``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    ai_dir = Path(args.ai_dir)
    if not ai_dir.is_dir():
        print(
            f"fourseer: error: AI directory not found or not a directory: {ai_dir}",
            file=sys.stderr,
        )
        return _MISSING_DIR_EXIT

    run = load_run(ai_dir)

    if args.command == "report":
        _emit(render_report(build_cycle_metrics(run)))
    elif args.command == "taxonomy":
        _emit(render_taxonomy(summarize_taxonomy(classify_run(run))))
    elif args.command == "drift":
        executed = {c.cycle_no for c in run.cycles}
        _emit(render_plan_drift(detect_plan_drift(run.gate_log, executed)))
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.error(f"unknown subcommand: {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
