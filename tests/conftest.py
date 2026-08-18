"""Shared pytest fixtures for fourseer tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_DEFAULT_SEED = Path("/home/sasha/AI/fourseer/seed")


def _resolve_seed() -> Path | None:
    """Locate the real seed dataset, or return None if it is not present.

    Resolution order: the ``FOURSEER_SEED`` environment variable, then the
    local default path. The seed is a local-only dataset (not committed to the
    repo), so it is absent on CI and most machines.
    """
    env = os.environ.get("FOURSEER_SEED")
    candidates = [Path(env)] if env else []
    candidates.append(_DEFAULT_SEED)
    for c in candidates:
        if c.is_dir():
            return c
    return None


@pytest.fixture
def seed_dir() -> Path:
    """The real seed dataset directory, or skip the test if it is absent.

    Tests that exercise the real seed dataset depend on this fixture. On CI /
    machines without the dataset the test is skipped (not failed); set
    ``FOURSEER_SEED`` to point at a copy to run them elsewhere.
    """
    seed = _resolve_seed()
    if seed is None:
        pytest.skip("seed dataset not present (set FOURSEER_SEED to run seed tests)")
    return seed
