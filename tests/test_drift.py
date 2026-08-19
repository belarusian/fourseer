"""Tests for :mod:`fourseer.drift` (issue drift detection).

Covers :func:`fourseer.drift.extract_closed_issues` (parsing ``#N`` references
from commit subjects — the ``Closes`` / ``Fixes`` / ``Resolves`` / ``Refs`` /
``See`` prefixes and bare ``#N`` — with per-commit dedup, cross-commit
dedup, and deterministic sorting by ``issue_no``), :func:`fourseer.drift.detect_issue_drift`
(the intersection with a set of still-open issues, deduped to the first
referencing commit in ``git log`` order, sorted by ``issue_no``), and
:func:`fourseer.drift.render_issue_drift` (the deterministic rendered block:
full / empty / determinism). Also verifies the :class:`IssueDrift` value object
is frozen, hashable, carries the ``commit_message`` field and the ``code``
machine tag (defaulting to ``"closed_but_still_open"``), and is re-exported from
the package root.

Most tests use small hand-built inline fixtures (not the full seed). Exactly
one test exercises real git history: it is gated on the ``seed_dir`` fixture
(skipped when the seed dataset is absent) but sources its commits from the
FOURSEER REPO'S OWN history (the seed has no ``.git``, so
``read_git_history(seed_dir)`` would raise).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

import fourseer
from fourseer.drift import (
    detect_issue_drift,
    detect_plan_drift,
    extract_closed_issues,
    planned_cycle_set,
    render_issue_drift,
    render_plan_drift,
)
from fourseer.models import BuildOrderRow, CommitRecord, GateLog, IssueDrift, PlanDrift


def _commit(hash: str, subject: str) -> CommitRecord:
    """A minimal :class:`CommitRecord` for a given hash / subject."""
    return CommitRecord(
        hash=hash,
        short_hash=hash[:7],
        author="sasha",
        date="2026-08-17 10:00:00",
        subject=subject,
    )


# ---------------------------------------------------------------------------
# extract_closed_issues
# ---------------------------------------------------------------------------


def test_extract_closes_prefix() -> None:
    """A ``Closes #N`` reference is extracted."""
    commits = [_commit("a" * 40, "Closes #42")]
    assert extract_closed_issues(commits) == [(42, "a" * 40, "Closes #42")]


def test_extract_fixes_prefix() -> None:
    """A ``Fixes #N`` reference is extracted."""
    commits = [_commit("b" * 40, "fix: Fixes #7")]
    assert extract_closed_issues(commits) == [(7, "b" * 40, "fix: Fixes #7")]


def test_extract_resolves_prefix() -> None:
    """A ``Resolves #N`` reference is extracted."""
    commits = [_commit("c" * 40, "Resolves #100")]
    assert extract_closed_issues(commits) == [(100, "c" * 40, "Resolves #100")]


def test_extract_refs_prefix() -> None:
    """A ``Refs #N`` reference is extracted."""
    commits = [_commit("d" * 40, "Refs #3")]
    assert extract_closed_issues(commits) == [(3, "d" * 40, "Refs #3")]


def test_extract_see_prefix() -> None:
    """A ``See #N`` reference is extracted."""
    commits = [_commit("e" * 40, "See #55 for context")]
    assert extract_closed_issues(commits) == [(55, "e" * 40, "See #55 for context")]


def test_extract_bare_hash() -> None:
    """A bare ``#N`` (no keyword) is extracted."""
    commits = [_commit("f" * 40, "wip #12")]
    assert extract_closed_issues(commits) == [(12, "f" * 40, "wip #12")]


def test_extract_multiple_in_one_subject() -> None:
    """A subject referencing several issues yields one tuple per issue."""
    commits = [_commit("g" * 40, "Closes #10 and #20")]
    assert extract_closed_issues(commits) == [
        (10, "g" * 40, "Closes #10 and #20"),
        (20, "g" * 40, "Closes #10 and #20"),
    ]


def test_extract_dedupes_within_subject() -> None:
    """The same issue referenced twice in one subject yields a single tuple."""
    commits = [_commit("h" * 40, "Closes #42, Fixes #42")]
    assert extract_closed_issues(commits) == [(42, "h" * 40, "Closes #42, Fixes #42")]


def test_extract_no_reference() -> None:
    """A subject with no ``#N`` yields nothing."""
    commits = [_commit("i" * 40, "no refs here")]
    assert extract_closed_issues(commits) == []


def test_extract_empty_commits() -> None:
    """An empty commit list yields an empty result."""
    assert extract_closed_issues([]) == []


def test_extract_sorted_by_issue_no() -> None:
    """The result is sorted by issue number, not by commit order."""
    commits = [
        _commit("a" * 40, "Closes #90"),
        _commit("b" * 40, "Closes #10"),
        _commit("c" * 40, "Closes #50"),
    ]
    assert extract_closed_issues(commits) == [
        (10, "b" * 40, "Closes #10"),
        (50, "c" * 40, "Closes #50"),
        (90, "a" * 40, "Closes #90"),
    ]


def test_extract_deterministic() -> None:
    """Repeated calls on the same input produce identical output."""
    commits = [
        _commit("a" * 40, "Closes #2"),
        _commit("b" * 40, "Closes #1"),
    ]
    assert extract_closed_issues(commits) == extract_closed_issues(commits)


def test_extract_does_not_mutate_input() -> None:
    """The input list is not mutated."""
    commits = [_commit("a" * 40, "Closes #1")]
    snapshot = list(commits)
    extract_closed_issues(commits)
    assert commits == snapshot


# ---------------------------------------------------------------------------
# detect_issue_drift
# ---------------------------------------------------------------------------


def test_drift_detects_open_referenced_issue() -> None:
    """An issue referenced by a commit and still open is reported."""
    commits = [_commit("a" * 40, "Closes #42")]
    drift = detect_issue_drift(commits, {42})
    assert drift == [
        IssueDrift(issue_no=42, commit_hash="a" * 40, commit_message="Closes #42")
    ]


def test_drift_ignores_closed_referenced_issue() -> None:
    """An issue referenced by a commit but NOT still open is not reported."""
    commits = [_commit("a" * 40, "Closes #42")]
    assert detect_issue_drift(commits, {99}) == []


def test_drift_ignores_unreferenced_open_issue() -> None:
    """An open issue that no commit references is not reported."""
    commits = [_commit("a" * 40, "Closes #42")]
    assert detect_issue_drift(commits, {7, 8}) == []


def test_drift_empty_open_set() -> None:
    """An empty open set yields no drift."""
    commits = [_commit("a" * 40, "Closes #42")]
    assert detect_issue_drift(commits, set()) == []


def test_drift_empty_commits() -> None:
    """An empty commit list yields no drift."""
    assert detect_issue_drift([], {1, 2, 3}) == []


def test_drift_dedupes_to_first_referencing_commit() -> None:
    """When several commits reference the same open issue, the FIRST (git log
    order, i.e. the first element of the list) is recorded."""
    commits = [
        _commit("a" * 40, "Closes #42"),  # newest first
        _commit("b" * 40, "Fixes #42"),
    ]
    drift = detect_issue_drift(commits, {42})
    assert drift == [
        IssueDrift(issue_no=42, commit_hash="a" * 40, commit_message="Closes #42")
    ]


def test_drift_sorted_by_issue_no() -> None:
    """The result is sorted by issue number."""
    commits = [
        _commit("a" * 40, "Closes #90"),
        _commit("b" * 40, "Closes #10"),
    ]
    drift = detect_issue_drift(commits, {10, 90})
    assert [d.issue_no for d in drift] == [10, 90]


def test_drift_multiple_issues() -> None:
    """Several drifted issues are all reported, one row each."""
    commits = [
        _commit("a" * 40, "Closes #10"),
        _commit("b" * 40, "Closes #20"),
    ]
    drift = detect_issue_drift(commits, {10, 20})
    assert drift == [
        IssueDrift(issue_no=10, commit_hash="a" * 40, commit_message="Closes #10"),
        IssueDrift(issue_no=20, commit_hash="b" * 40, commit_message="Closes #20"),
    ]


def test_drift_code_defaults_to_closed_but_still_open() -> None:
    """Every detected drift row carries the stable ``code`` machine tag."""
    commits = [_commit("a" * 40, "Closes #42")]
    drift = detect_issue_drift(commits, {42})
    assert drift
    assert all(d.code == "closed_but_still_open" for d in drift)


def test_drift_deterministic() -> None:
    """Repeated calls on the same input produce identical output."""
    commits = [
        _commit("a" * 40, "Closes #2"),
        _commit("b" * 40, "Closes #1"),
    ]
    assert detect_issue_drift(commits, {1, 2}) == detect_issue_drift(commits, {1, 2})


def test_drift_does_not_mutate_inputs() -> None:
    """Neither the commit list nor the open set is mutated."""
    commits = [_commit("a" * 40, "Closes #1")]
    open_issues = {1, 2}
    snapshot = list(commits)
    open_snapshot = set(open_issues)
    detect_issue_drift(commits, open_issues)
    assert commits == snapshot
    assert open_issues == open_snapshot


# ---------------------------------------------------------------------------
# render_issue_drift
# ---------------------------------------------------------------------------


def test_render_empty() -> None:
    """An empty drift renders the stable no-drift line."""
    out = render_issue_drift([])
    assert out == "# Issue Drift (0 issues)\nno issue drift detected\n"


def test_render_single() -> None:
    """A single drifted issue renders one line under the header."""
    drift = [IssueDrift(issue_no=42, commit_hash="a" * 40, commit_message="Closes #42")]
    out = render_issue_drift(drift)
    assert out == (
        "# Issue Drift (1 issues)\n"
        f"#42: Closes #42 ({'a' * 40})\n"
    )


def test_render_multiple_sorted() -> None:
    """Multiple issues render one line each, sorted by issue number."""
    drift = [
        IssueDrift(issue_no=20, commit_hash="b" * 40, commit_message="Closes #20"),
        IssueDrift(issue_no=10, commit_hash="a" * 40, commit_message="Closes #10"),
    ]
    out = render_issue_drift(drift)
    assert out == (
        "# Issue Drift (2 issues)\n"
        f"#10: Closes #10 ({'a' * 40})\n"
        f"#20: Closes #20 ({'b' * 40})\n"
    )


def test_render_header_counts_issues() -> None:
    """The header's count matches the number of drift rows."""
    drift = [
        IssueDrift(issue_no=1, commit_hash="a" * 40, commit_message="s1"),
        IssueDrift(issue_no=2, commit_hash="b" * 40, commit_message="s2"),
        IssueDrift(issue_no=3, commit_hash="c" * 40, commit_message="s3"),
    ]
    assert render_issue_drift(drift).startswith("# Issue Drift (3 issues)\n")


def test_render_ends_with_newline() -> None:
    """The rendered block always ends with a trailing newline."""
    assert render_issue_drift([]).endswith("\n")
    assert render_issue_drift(
        [IssueDrift(issue_no=1, commit_hash="a" * 40, commit_message="s")]
    ).endswith("\n")


def test_render_deterministic() -> None:
    """Repeated calls on the same input produce identical output."""
    drift = [IssueDrift(issue_no=5, commit_hash="a" * 40, commit_message="Closes #5")]
    assert render_issue_drift(drift) == render_issue_drift(drift)


def test_render_does_not_mutate_input() -> None:
    """The input list is not mutated (rendering sorts a copy)."""
    drift = [
        IssueDrift(issue_no=20, commit_hash="b" * 40, commit_message="Closes #20"),
        IssueDrift(issue_no=10, commit_hash="a" * 40, commit_message="Closes #10"),
    ]
    snapshot = list(drift)
    render_issue_drift(drift)
    assert drift == snapshot


# ---------------------------------------------------------------------------
# IssueDrift value object
# ---------------------------------------------------------------------------


def test_issue_drift_fields() -> None:
    """IssueDrift carries issue_no / commit_hash / commit_message / code."""
    d = IssueDrift(
        issue_no=42,
        commit_hash="a" * 40,
        commit_message="Closes #42",
        code="closed_but_still_open",
    )
    assert d.issue_no == 42
    assert d.commit_hash == "a" * 40
    assert d.commit_message == "Closes #42"
    assert d.code == "closed_but_still_open"


def test_issue_drift_code_defaults() -> None:
    """Omitting ``code`` defaults it to the stable machine tag."""
    d = IssueDrift(issue_no=42, commit_hash="a" * 40, commit_message="Closes #42")
    assert d.code == "closed_but_still_open"


def test_issue_drift_is_frozen() -> None:
    """IssueDrift is a frozen dataclass: mutation raises."""
    d = IssueDrift(issue_no=1, commit_hash="h", commit_message="s")
    assert dataclasses.is_dataclass(d)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.issue_no = 99


def test_issue_drift_hashable_and_equal() -> None:
    """Two identical IssueDrift instances compare equal and hash equal."""
    a = IssueDrift(issue_no=1, commit_hash="h", commit_message="s")
    b = IssueDrift(issue_no=1, commit_hash="h", commit_message="s")
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


# ---------------------------------------------------------------------------
# package-root re-exports
# ---------------------------------------------------------------------------


def test_public_api_reexports_drift() -> None:
    """The four drift symbols are importable from the package root and in __all__."""
    assert fourseer.extract_closed_issues is extract_closed_issues
    assert fourseer.detect_issue_drift is detect_issue_drift
    assert fourseer.render_issue_drift is render_issue_drift
    assert fourseer.IssueDrift is IssueDrift
    for name in (
        "IssueDrift",
        "extract_closed_issues",
        "detect_issue_drift",
        "render_issue_drift",
    ):
        assert name in fourseer.__all__


# ---------------------------------------------------------------------------
# real git history (the fourseer repo's OWN history)
# ---------------------------------------------------------------------------


def test_drift_against_fourseer_repo_history(seed_dir) -> None:
    """Exercise real git history, gated on the ``seed_dir`` fixture.

    The seed dataset has no ``.git`` (so ``read_git_history(seed_dir)`` would
    raise), so this test sources its commits from the FOURSEER REPO'S OWN
    history instead. The merge commits reference PRs 6, 11, 17, 23, 29, 35,
    41, 47; every one of them is closed, so an empty open set yields no drift.
    """
    from fourseer.parse import read_git_history

    # The fourseer repo root is the parent of this test file's directory.
    repo_root = Path(__file__).resolve().parent.parent
    commits = read_git_history(repo_root)
    assert commits, "fourseer repo git history should be non-empty"

    refs = extract_closed_issues(commits)
    assert refs, "fourseer commit subjects should reference at least one issue/PR"

    # The referenced issue numbers form a non-empty, stable set.
    referenced = {issue_no for issue_no, _h, _s in refs}
    assert referenced

    # The merge commits reference PRs 6, 11, 17, 23, 29, 35, 41, 47. Pin that
    # stable subset: every one of these must be among the referenced numbers.
    stable_subset = {6, 11, 17, 23, 29, 35, 41, 47}
    assert stable_subset <= referenced

    # No issue is still open -> no drift.
    assert detect_issue_drift(commits, set()) == []


# ---------------------------------------------------------------------------
# planned_cycle_set
# ---------------------------------------------------------------------------


def _row(cycles: str, phase: str = "P", target: str = "t") -> BuildOrderRow:
    """A minimal :class:`BuildOrderRow` for a given ``cycles`` cell."""
    return BuildOrderRow(phase=phase, cycles=cycles, target=target)


def test_planned_single_range() -> None:
    """A ``"1-3"`` range yields the inclusive set {1, 2, 3}."""
    gate = GateLog(build_order=[_row("1-3")])
    assert planned_cycle_set(gate) == {1, 2, 3}


def test_planned_single_cycle() -> None:
    """A bare ``"7"`` cell yields the single-cycle set {7}."""
    gate = GateLog(build_order=[_row("7")])
    assert planned_cycle_set(gate) == {7}


def test_planned_union_across_rows() -> None:
    """Multiple rows are unioned into one set."""
    gate = GateLog(build_order=[_row("1-3"), _row("5"), _row("7-9")])
    assert planned_cycle_set(gate) == {1, 2, 3, 5, 7, 8, 9}


def test_planned_overlapping_rows_dedup() -> None:
    """Overlapping ranges dedup into a single set."""
    gate = GateLog(build_order=[_row("1-5"), _row("3-7")])
    assert planned_cycle_set(gate) == {1, 2, 3, 4, 5, 6, 7}


def test_planned_empty_build_order() -> None:
    """No Build Order rows yields the empty set."""
    assert planned_cycle_set(GateLog()) == set()
    assert planned_cycle_set(GateLog(build_order=[])) == set()


def test_planned_tolerates_unparseable() -> None:
    """Unparseable cells contribute nothing (no raise)."""
    gate = GateLog(build_order=[_row("TBD"), _row(""), _row("1-3-5"), _row("2")])
    assert planned_cycle_set(gate) == {2}


def test_planned_tolerates_reversed_range() -> None:
    """A reversed range (``"5-2"``) is treated as unparseable."""
    gate = GateLog(build_order=[_row("5-2"), _row("4")])
    assert planned_cycle_set(gate) == {4}


def test_planned_tolerates_whitespace() -> None:
    """Whitespace around range tokens is tolerated."""
    gate = GateLog(build_order=[_row(" 1 - 3 "), _row(" 7 ")])
    assert planned_cycle_set(gate) == {1, 2, 3, 7}


def test_planned_does_not_mutate_input() -> None:
    """The gate log is not mutated."""
    gate = GateLog(build_order=[_row("1-3")])
    snapshot = list(gate.build_order)
    planned_cycle_set(gate)
    assert gate.build_order == snapshot


# ---------------------------------------------------------------------------
# detect_plan_drift
# ---------------------------------------------------------------------------


def test_drift_empty_when_planned_equals_executed() -> None:
    """No drift when the plan and the executed set agree exactly."""
    gate = GateLog(build_order=[_row("1-3")])
    assert detect_plan_drift(gate, {1, 2, 3}) == []


def test_drift_executed_not_planned() -> None:
    """Cycles executed but not planned are tagged executed_not_planned."""
    gate = GateLog(build_order=[_row("1-3")])
    drift = detect_plan_drift(gate, {1, 2, 3, 5, 6})
    assert drift == [
        PlanDrift(cycle_no=5, status="executed_not_planned"),
        PlanDrift(cycle_no=6, status="executed_not_planned"),
    ]


def test_drift_planned_not_executed() -> None:
    """Cycles planned but not executed are tagged planned_not_executed."""
    gate = GateLog(build_order=[_row("1-3")])
    drift = detect_plan_drift(gate, {1})
    assert drift == [
        PlanDrift(cycle_no=2, status="planned_not_executed"),
        PlanDrift(cycle_no=3, status="planned_not_executed"),
    ]


def test_drift_both_directions_sorted_by_cycle_no() -> None:
    """Drift from both directions is merged and sorted by cycle_no."""
    gate = GateLog(build_order=[_row("1-3")])
    drift = detect_plan_drift(gate, {3, 5})
    assert drift == [
        PlanDrift(cycle_no=1, status="planned_not_executed"),
        PlanDrift(cycle_no=2, status="planned_not_executed"),
        PlanDrift(cycle_no=5, status="executed_not_planned"),
    ]


def test_drift_common_cycles_produce_no_row() -> None:
    """A cycle in both sets is on-plan and yields no row."""
    gate = GateLog(build_order=[_row("1-3")])
    drift = detect_plan_drift(gate, {1, 2, 3, 4})
    # 1, 2, 3 are common -> no rows; only 4 (executed_not_planned) remains.
    assert drift == [PlanDrift(cycle_no=4, status="executed_not_planned")]


def test_drift_empty_build_order_all_executed_not_planned() -> None:
    """An empty Build Order means every executed cycle is executed_not_planned."""
    gate = GateLog()
    drift = detect_plan_drift(gate, {2, 1})
    assert drift == [
        PlanDrift(cycle_no=1, status="executed_not_planned"),
        PlanDrift(cycle_no=2, status="executed_not_planned"),
    ]


def test_drift_empty_executed_all_planned_not_executed() -> None:
    """An empty executed set means every planned cycle is planned_not_executed."""
    gate = GateLog(build_order=[_row("1-3")])
    drift = detect_plan_drift(gate, set())
    assert drift == [
        PlanDrift(cycle_no=1, status="planned_not_executed"),
        PlanDrift(cycle_no=2, status="planned_not_executed"),
        PlanDrift(cycle_no=3, status="planned_not_executed"),
    ]


def test_drift_both_empty() -> None:
    """Empty Build Order and empty executed set yield no drift."""
    assert detect_plan_drift(GateLog(), set()) == []


def test_drift_deduped_one_row_per_cycle() -> None:
    """Each drifted cycle appears exactly once (no duplicate rows)."""
    gate = GateLog(build_order=[_row("1-3"), _row("1-3")])
    drift = detect_plan_drift(gate, {3, 5})
    cycle_nos = [d.cycle_no for d in drift]
    assert cycle_nos == sorted(cycle_nos)
    assert len(cycle_nos) == len(set(cycle_nos))


def test_drift_code_defaults_to_plan_drift() -> None:
    """Every emitted row carries the default ``plan_drift`` code."""
    gate = GateLog(build_order=[_row("1-3")])
    for d in detect_plan_drift(gate, {3, 5}):
        assert d.code == "plan_drift"


def test_detect_plan_drift_deterministic() -> None:
    """Repeated calls on the same input produce identical output."""
    gate = GateLog(build_order=[_row("1-3")])
    assert detect_plan_drift(gate, {3, 5}) == detect_plan_drift(gate, {3, 5})


def test_detect_plan_drift_does_not_mutate_inputs() -> None:
    """Neither the gate log nor the executed set is mutated."""
    gate = GateLog(build_order=[_row("1-3")])
    executed = {3, 5}
    snapshot_rows = list(gate.build_order)
    snapshot_executed = set(executed)
    detect_plan_drift(gate, executed)
    assert gate.build_order == snapshot_rows
    assert executed == snapshot_executed


# ---------------------------------------------------------------------------
# render_plan_drift
# ---------------------------------------------------------------------------


def test_render_plan_drift_empty() -> None:
    """An empty list renders the stable no-drift line."""
    assert render_plan_drift([]) == "# Plan Drift (0 cycles)\nno plan drift detected\n"


def test_render_plan_drift_single() -> None:
    """A single row renders one ``cycle <n>: <status>`` line."""
    drift = [PlanDrift(cycle_no=5, status="executed_not_planned")]
    assert render_plan_drift(drift) == (
        "# Plan Drift (1 cycles)\n"
        "cycle 5: executed_not_planned\n"
    )


def test_render_plan_drift_multiple_sorted() -> None:
    """Rows render in cycle_no order regardless of input order."""
    drift = [
        PlanDrift(cycle_no=5, status="executed_not_planned"),
        PlanDrift(cycle_no=1, status="planned_not_executed"),
        PlanDrift(cycle_no=3, status="planned_not_executed"),
    ]
    assert render_plan_drift(drift) == (
        "# Plan Drift (3 cycles)\n"
        "cycle 1: planned_not_executed\n"
        "cycle 3: planned_not_executed\n"
        "cycle 5: executed_not_planned\n"
    )


def test_render_plan_drift_header_counts_cycles() -> None:
    """The header reports the number of drifted cycles."""
    drift = [
        PlanDrift(cycle_no=1, status="planned_not_executed"),
        PlanDrift(cycle_no=2, status="planned_not_executed"),
        PlanDrift(cycle_no=3, status="planned_not_executed"),
    ]
    assert render_plan_drift(drift).startswith("# Plan Drift (3 cycles)\n")


def test_render_plan_drift_ends_with_newline() -> None:
    """The rendered block always ends with a trailing newline."""
    assert render_plan_drift([]).endswith("\n")
    assert render_plan_drift(
        [PlanDrift(cycle_no=1, status="planned_not_executed")]
    ).endswith("\n")


def test_render_plan_drift_deterministic() -> None:
    """Repeated calls on the same input produce identical output."""
    drift = [PlanDrift(cycle_no=5, status="executed_not_planned")]
    assert render_plan_drift(drift) == render_plan_drift(drift)


def test_render_plan_drift_does_not_mutate_input() -> None:
    """The input list is not mutated (rendering sorts a copy)."""
    drift = [
        PlanDrift(cycle_no=20, status="executed_not_planned"),
        PlanDrift(cycle_no=10, status="planned_not_executed"),
    ]
    snapshot = list(drift)
    render_plan_drift(drift)
    assert drift == snapshot


# ---------------------------------------------------------------------------
# PlanDrift value object
# ---------------------------------------------------------------------------


def test_plan_drift_fields() -> None:
    """PlanDrift carries cycle_no / status / code."""
    d = PlanDrift(cycle_no=7, status="executed_not_planned", code="plan_drift")
    assert d.cycle_no == 7
    assert d.status == "executed_not_planned"
    assert d.code == "plan_drift"


def test_plan_drift_code_defaults() -> None:
    """Omitting ``code`` defaults it to the stable machine tag."""
    d = PlanDrift(cycle_no=7, status="planned_not_executed")
    assert d.code == "plan_drift"


def test_plan_drift_is_frozen() -> None:
    """PlanDrift is a frozen dataclass: mutation raises."""
    d = PlanDrift(cycle_no=1, status="executed_not_planned")
    assert dataclasses.is_dataclass(d)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.cycle_no = 99


def test_plan_drift_hashable_and_equal() -> None:
    """Two identical PlanDrift instances compare equal and hash equal."""
    a = PlanDrift(cycle_no=1, status="executed_not_planned")
    b = PlanDrift(cycle_no=1, status="executed_not_planned")
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_plan_drift_distinct_status_not_equal() -> None:
    """Two PlanDrift rows differing only in status are not equal."""
    a = PlanDrift(cycle_no=1, status="executed_not_planned")
    b = PlanDrift(cycle_no=1, status="planned_not_executed")
    assert a != b


# ---------------------------------------------------------------------------
# package-root re-exports (plan drift)
# ---------------------------------------------------------------------------


def test_public_api_reexports_plan_drift() -> None:
    """The plan-drift symbols are importable from the package root and in __all__."""
    assert fourseer.planned_cycle_set is planned_cycle_set
    assert fourseer.detect_plan_drift is detect_plan_drift
    assert fourseer.render_plan_drift is render_plan_drift
    assert fourseer.PlanDrift is PlanDrift
    for name in (
        "PlanDrift",
        "planned_cycle_set",
        "detect_plan_drift",
        "render_plan_drift",
    ):
        assert name in fourseer.__all__


# ---------------------------------------------------------------------------
# real seed (gated on the seed_dir fixture)
# ---------------------------------------------------------------------------


def test_plan_drift_against_real_seed(seed_dir) -> None:
    """Run plan drift on the real seed and pin the expected drift sets.

    The seed's Build Order plans cycles 1-20 (six ranges: 1-3, 4-6, 7-9,
    10-13, 14-17, 18-20); its ``cycles.out`` executed cycles 7-28. So the
    drift is: executed_not_planned {21..28} and planned_not_executed {1..6}.
    """
    from fourseer.load import load_run

    run = load_run(seed_dir)
    executed = {c.cycle_no for c in run.cycles}

    planned = planned_cycle_set(run.gate_log)
    assert planned == set(range(1, 21))
    assert executed == set(range(7, 29))

    drift = detect_plan_drift(run.gate_log, executed)
    executed_not_planned = {
        d.cycle_no for d in drift if d.status == "executed_not_planned"
    }
    planned_not_executed = {
        d.cycle_no for d in drift if d.status == "planned_not_executed"
    }
    assert executed_not_planned == {21, 22, 23, 24, 25, 26, 27, 28}
    assert planned_not_executed == {1, 2, 3, 4, 5, 6}

    # One row per drifted cycle, sorted by cycle_no, no overlap between sets.
    cycle_nos = [d.cycle_no for d in drift]
    assert cycle_nos == sorted(cycle_nos)
    assert len(cycle_nos) == len(set(cycle_nos))
    assert executed_not_planned.isdisjoint(planned_not_executed)
    assert len(drift) == len(executed_not_planned) + len(planned_not_executed)
