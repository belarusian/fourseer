"""Issue drift detection for a :class:`~fourseer.models.Run`'s commit history.

Issue drift is the set of issues that a commit *claims* to have closed (via a
``Closes`` / ``Fixes`` / ``Resolves`` / ``Refs`` / ``See`` reference, or a bare
``#N`` in the commit subject) but that are in fact *still open*. It is the
cross-check between the git history (which references closed issues) and a
caller-supplied set of still-open issue numbers.

The three public functions are pure, deterministic, stdlib-only, and perform no
I/O and never mutate their inputs:

- :func:`extract_closed_issues` — parse commit subjects for issue references
  (``#N``), returning a sorted, deduped list of
  ``(issue_no, commit_hash, commit_message)`` tuples.
- :func:`detect_issue_drift` — intersect those references with a set of
  still-open issue numbers, returning one
  :class:`~fourseer.models.IssueDrift` per drifted issue (deduped to the first
  referencing commit, sorted by ``issue_no``).
- :func:`render_issue_drift` — render a drift list as a short, deterministic
  human-readable block.
"""

from __future__ import annotations

import re

from fourseer.models import CommitRecord, IssueDrift

__all__ = ["detect_issue_drift", "extract_closed_issues", "render_issue_drift"]

# Any ``#N`` token in a subject is an issue reference. This covers the
# ``Closes`` / ``Fixes`` / ``Resolves`` / ``Refs`` / ``See`` prefixes (each of
# which is followed by ``#N``) as well as a bare ``#N``.
_ISSUE_REF = re.compile(r"#(\d+)")


def _issue_refs(subject: str) -> list[int]:
    """Return the issue numbers referenced in *subject*.

    A reference is any ``#N`` token (see :data:`_ISSUE_REF`). The numbers are
    returned in order of first appearance and deduped, so a subject that
    references the same issue twice (e.g. ``"Closes #42, Fixes #42"``) yields
    ``[42]``.
    """
    seen: set[int] = set()
    refs: list[int] = []
    for match in _ISSUE_REF.finditer(subject):
        n = int(match.group(1))
        if n not in seen:
            seen.add(n)
            refs.append(n)
    return refs


def extract_closed_issues(commits: list[CommitRecord]) -> list[tuple[int, str, str]]:
    """Extract every issue referenced by a commit's subject.

    For each commit (in the order given), every ``#N`` in its subject yields a
    ``(issue_no, commit_hash, commit_message)`` tuple. The result is deduped —
    a commit that references the same issue more than once yields a single
    tuple — and sorted by ``issue_no`` (ties broken by the commit's position in
    *commits*, so the order is fully deterministic).

    Pure, deterministic, stdlib-only; never mutates *commits*.

    Parameters
    ----------
    commits:
        The commits to scan (typically the output of
        :func:`fourseer.parse.read_git_history`, in ``git log`` order). Never
        mutated.

    Returns
    -------
    list[tuple[int, str, str]]
        One ``(issue_no, commit_hash, commit_message)`` per distinct
        (issue, commit) reference, sorted by ``issue_no``.
    """
    pairs: list[tuple[int, int, str, str]] = []  # (issue_no, commit_index, hash, subject)
    seen: set[tuple[int, str]] = set()
    for idx, commit in enumerate(commits):
        for issue_no in _issue_refs(commit.subject):
            key = (issue_no, commit.hash)
            if key in seen:
                continue
            seen.add(key)
            pairs.append((issue_no, idx, commit.hash, commit.subject))
    pairs.sort(key=lambda p: (p[0], p[1]))
    return [(issue_no, commit_hash, subject) for issue_no, _idx, commit_hash, subject in pairs]


def detect_issue_drift(
    commits: list[CommitRecord], open_issues: set[int]
) -> list[IssueDrift]:
    """Detect issues a commit claims to have closed but that are still open.

    An issue is *drifted* when it is referenced by at least one commit subject
    (see :func:`extract_closed_issues`) AND its number is in *open_issues*. For
    each drifted issue the FIRST referencing commit — in the order *commits* is
    given (``git log`` order, i.e. newest first) — is recorded. The result is
    deduped to one :class:`~fourseer.models.IssueDrift` per issue and sorted by
    ``issue_no``.

    Pure, deterministic, stdlib-only; never mutates *commits* or *open_issues*.

    Parameters
    ----------
    commits:
        The commits to scan (typically the output of
        :func:`fourseer.parse.read_git_history`). Never mutated.
    open_issues:
        The set of issue numbers that are still open. Never mutated.

    Returns
    -------
    list[IssueDrift]
        One :class:`~fourseer.models.IssueDrift` per drifted issue, sorted by
        ``issue_no``. Empty when no referenced issue is still open.
    """
    first: dict[int, tuple[str, str]] = {}
    for commit in commits:
        for issue_no in _issue_refs(commit.subject):
            if issue_no in open_issues and issue_no not in first:
                first[issue_no] = (commit.hash, commit.subject)
    return [
        IssueDrift(issue_no=no, commit_hash=commit_hash, commit_message=subject)
        for no, (commit_hash, subject) in sorted(first.items())
    ]


def render_issue_drift(drift: list[IssueDrift]) -> str:
    """Render a list of :class:`~fourseer.models.IssueDrift` as a short block.

    A pure, deterministic, stdlib-only string transformation, consistent in
    style with :func:`fourseer.report.render_summary` and
    :func:`fourseer.taxonomy.render_taxonomy`:

    - a header line ``# Issue Drift (N issues)`` where ``N`` is ``len(drift)``;
    - when *drift* is non-empty, one line per issue in ``issue_no`` order of the
      form ``#<issue_no>: <commit_message> (<commit_hash>)``;
    - when *drift* is empty, a single stable no-drift line
      ``no issue drift detected``.

    The output always ends with a trailing newline.

    Parameters
    ----------
    drift:
        The drift rows to render (typically the output of
        :func:`detect_issue_drift`). Never mutated.

    Returns
    -------
    str
        The rendered drift block, ending with a trailing newline.
    """
    lines: list[str] = [f"# Issue Drift ({len(drift)} issues)"]
    if drift:
        for d in sorted(drift, key=lambda d: d.issue_no):
            lines.append(f"#{d.issue_no}: {d.commit_message} ({d.commit_hash})")
    else:
        lines.append("no issue drift detected")
    return "\n".join(lines) + "\n"
