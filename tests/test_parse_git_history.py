"""Tests for :func:`fourseer.parse.git_history.read_git_history`.

Covers the git-history reader (TICKET-005): reading the fourseer repo itself,
a temp git repo created via subprocess (newest-first ordering), and the
``FileNotFoundError`` for a missing path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from fourseer.parse.git_history import read_git_history

# The fourseer repo is the project root (this test file lives in tests/).
FOURSEER_REPO = Path(__file__).resolve().parent.parent


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def test_fourseer_repo_itself() -> None:
    """Reading the fourseer repo yields >=1 record with populated fields."""
    records = read_git_history(FOURSEER_REPO)
    assert len(records) >= 1
    rec = records[0]
    assert rec.hash and len(rec.hash) == 40
    assert rec.short_hash
    assert rec.hash.startswith(rec.short_hash)  # short_hash is a prefix of hash
    assert rec.author
    assert rec.date
    assert rec.subject


def test_temp_repo_newest_first(tmp_path: Path) -> None:
    """A temp repo with 2 commits returns them newest-first."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test Author")

    (tmp_path / "a.txt").write_text("first", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-q", "-m", "first commit")

    (tmp_path / "b.txt").write_text("second", encoding="utf-8")
    _git(tmp_path, "add", "b.txt")
    _git(tmp_path, "commit", "-q", "-m", "second commit")

    records = read_git_history(tmp_path)
    assert len(records) == 2
    # Newest first: the second commit is at index 0.
    assert records[0].subject == "second commit"
    assert records[1].subject == "first commit"
    for rec in records:
        assert rec.hash.startswith(rec.short_hash)
        assert rec.author == "Test Author"


def test_missing_path_raises() -> None:
    """A non-existent path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_git_history(Path("/does/not/exist/anywhere"))
