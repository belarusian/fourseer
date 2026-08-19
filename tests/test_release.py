"""Release guard: the package version is a single logical value.

Asserts that :data:`fourseer.__version__` is the release version and that it
matches the ``version`` field in ``pyproject.toml``. The pyproject value is
parsed with a minimal regex (the package is not installed, so
``importlib.metadata`` is deliberately not used).
"""

from __future__ import annotations

import re
from pathlib import Path

import fourseer

_RELEASE_VERSION = "1.0.0"
_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _pyproject_version() -> str:
    """Parse the ``version = "..."`` field out of pyproject.toml."""
    text = _PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    assert match is not None, "no version field found in pyproject.toml"
    return match.group(1)


def test_version_is_release() -> None:
    """fourseer.__version__ is the release version."""
    assert fourseer.__version__ == _RELEASE_VERSION


def test_version_matches_pyproject() -> None:
    """fourseer.__version__ equals the version parsed from pyproject.toml."""
    assert fourseer.__version__ == _pyproject_version()
