"""Read a git repository's history into :class:`~fourseer.models.CommitRecord`.

Uses ``git log`` via :mod:`subprocess` with a fixed, unambiguous format string
so the output is parseable without ambiguity. Only the standard library is used.

The format string is::

    %H%x1f%h%x1f%an%x1f%ad%x1f%s

with ``--date=iso``. Fields are separated by the unit-separator byte (``\\x1f``)
so that commit subjects containing ``|`` or other punctuation cannot break the
parse.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from fourseer.models import CommitRecord

__all__ = ["read_git_history"]

_FORMAT = "%H\x1f%h\x1f%an\x1f%ad\x1f%s"
_SEP = "\x1f"


def read_git_history(repo_path: str | Path) -> list[CommitRecord]:
    """Read the commit history of the git repo at *repo_path*.

    Parameters
    ----------
    repo_path:
        Path to a git working tree (any directory inside the repo works).

    Returns
    -------
    list[CommitRecord]
        Commits in ``git log`` order (newest first).

    Raises
    ------
    FileNotFoundError
        If *repo_path* does not exist.
    RuntimeError
        If ``git log`` fails (e.g. not a git repository).
    """
    p = Path(repo_path)
    if not p.exists():
        raise FileNotFoundError(f"repo path does not exist: {p}")

    result = subprocess.run(
        ["git", "-C", str(p), "log", f"--pretty=format:{_FORMAT}", "--date=iso"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git log failed: {result.stderr.strip()}")

    records: list[CommitRecord] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(_SEP)
        if len(parts) != 5:
            continue
        full_hash, short_hash, author, date, subject = parts
        records.append(
            CommitRecord(
                hash=full_hash,
                short_hash=short_hash,
                author=author,
                date=date,
                subject=subject,
            )
        )
    return records
