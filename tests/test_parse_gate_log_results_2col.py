"""Tests for the 2-column ``### Results`` gate-log dialect (TICKET-057/059).

The seed uses a 3-column ``| Check | Before | After |`` table under
``### Results``. The launch-gate and fourseer dialects instead use a 2-column
``| Check | Result |`` table under the same ``### Results`` header. These tests
pin the parser's handling of that 2-column dialect:

- a ``PR #<n>`` / ``PR <n>`` row whose second cell contains ``MERGED`` (any
  case) sets ``merged`` to ``True``;
- a ``gate`` / ``pytest`` / ``build+test`` / ``build`` row drives
  ``gate_after`` from the second cell;
- a ``Merged on main`` / ``Merge commit on main`` row with a non-dash second
  cell sets ``merged`` to ``True``;
- a row with no merge evidence leaves ``merged`` ``None``;
- the existing 3-column seed dialect still works (regression guard).
"""

from __future__ import annotations

from fourseer.parse.gate_log import parse_gate_log


def _block(text: str, cycle_no: int):
    gl = parse_gate_log(text)
    return next(b for b in gl.cycles if b.cycle_no == cycle_no)


# --- PR row + gate row (launch-gate dialect) --------------------------------


def test_pr_merged_row_sets_merged_and_gate_green() -> None:
    """A ``PR #57 | MERGED ...`` row sets merged; the pytest row sets green."""
    text = (
        "## Cycle 13: Launch gate\n"
        "**Date:** 2026-08-20\n"
        "\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| PR #57 | MERGED (merge commit 247f879) |\n"
        "| pytest tests/ -x -q | 199 passed |\n"
    )
    b = _block(text, 13)
    assert b.merged is True
    assert b.gate_after == "green"


def test_pr_row_without_hash_still_matches() -> None:
    """``PR 57`` (no ``#``) is recognized as a PR row."""
    text = (
        "## Cycle 14: Wire\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| PR 57 | merged |\n"
    )
    assert _block(text, 14).merged is True


def test_pr_row_not_merged_leaves_merged_none() -> None:
    """A ``PR`` row whose second cell lacks ``MERGED`` does not set merged."""
    text = (
        "## Cycle 7: Open\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| PR #12 | OPEN (review pending) |\n"
        "| pytest tests/ -x -q | 10 passed |\n"
    )
    b = _block(text, 7)
    assert b.merged is None
    assert b.gate_after == "green"


# --- gate row variants ------------------------------------------------------


def test_gate_label_row_drives_green() -> None:
    """A ``gate | green`` row drives gate_after to green."""
    text = (
        "## Cycle 10: Docs\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| gate | green |\n"
    )
    assert _block(text, 10).gate_after == "green"


def test_build_plus_test_row_drives_green() -> None:
    """A ``build+test | 12 passed`` row drives gate_after to green."""
    text = (
        "## Cycle 9: Flags\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| build+test | 12 passed |\n"
    )
    assert _block(text, 9).gate_after == "green"


def test_pytest_row_drives_red_on_failure() -> None:
    """A failing pytest row drives gate_after to red."""
    text = (
        "## Cycle 5: Broken\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| pytest tests/ -x -q | 3 failed, 37 passed |\n"
    )
    assert _block(text, 5).gate_after == "red"


# --- Merged on main / Merge commit on main rows -----------------------------


def test_merged_on_main_2col_sets_merged() -> None:
    """A ``Merged on main`` row with a non-dash cell sets merged True."""
    text = (
        "## Cycle 11: Docs\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| gate | green |\n"
        "| Merged on main | 8312b08 (PR #6) |\n"
    )
    b = _block(text, 11)
    assert b.merged is True
    assert b.gate_after == "green"


def test_merge_commit_on_main_sets_merged() -> None:
    """A ``Merge commit on main`` row with a hash sets merged True."""
    text = (
        "## Cycle 12: Flags\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| build+test | 12 passed |\n"
        "| Merge commit on main | 9d3f9bb |\n"
    )
    b = _block(text, 12)
    assert b.merged is True
    assert b.gate_after == "green"


def test_merged_on_main_dash_leaves_merged_none() -> None:
    """A ``Merged on main`` row with a dash cell does not set merged."""
    text = (
        "## Cycle 15: Pending\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| gate | green |\n"
        "| Merged on main | — |\n"
    )
    b = _block(text, 15)
    assert b.merged is None
    assert b.gate_after == "green"


# --- no merge evidence ------------------------------------------------------


def test_no_merge_evidence_leaves_merged_none() -> None:
    """A table with only a pytest row and an issues row leaves merged None."""
    text = (
        "## Cycle 4: Issues\n"
        "### Results\n"
        "| Check | Result |\n"
        "|---|---|\n"
        "| pytest tests/ -x -q | 40 passed |\n"
        "| Issues #1-#5 | CLOSED |\n"
    )
    b = _block(text, 4)
    assert b.merged is None
    assert b.gate_after == "green"


# --- 3-column seed dialect regression guard ---------------------------------


def test_three_column_seed_dialect_still_works() -> None:
    """The 3-column ``| Check | Before | After |`` dialect is unchanged."""
    text = (
        "## Cycle 2: Foundations\n"
        "### Results\n"
        "| Check | Before | After |\n"
        "|---|---|---|\n"
        "| Gate (build+test+lint) | RED | GREEN |\n"
        "| Merged on main | — | 8312b08 (PR #6) |\n"
    )
    b = _block(text, 2)
    assert b.gate_after == "green"
    assert b.merged is True
