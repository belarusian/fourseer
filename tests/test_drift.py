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
from fourseer.drift import detect_issue_drift, extract_closed_issues, render_issue_drift
from fourseer.models import CommitRecord, IssueDrift


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
