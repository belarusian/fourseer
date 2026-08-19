# TICKET-056: Release version bump to 0.2.0 + single-source-of-truth guard

## Title
Bump the release version from `0.1.0` to `0.2.0` (the CLI entrypoint shipped
in build 11 is a new user-facing capability) and add a test that keeps
`pyproject.toml` and `fourseer/__init__.py` in sync.

## Evidence
The version is duplicated in two places and currently at `0.1.0`:
- `pyproject.toml:7`  `version = "0.1.0"`
- `fourseer/__init__.py:62`  `__version__ = "0.1.0"`

The package has since shipped a complete, tested CLI entrypoint
(`fourseer/cli.py`, `fourseer/__main__.py`, console script at
`pyproject.toml:23`) — a new user-facing surface beyond the original
library-only `0.1.0`. No release has been cut since.

No test guards the two copies against drifting apart. `tests/test_smoke.py:5`
only asserts `fourseer.__version__` is a non-empty string; it does not compare
it to the `pyproject.toml` value.

## Impact
- The published version understates the shipped capability (a working CLI is
  present but the version still reads `0.1.0`).
- The two version strings can silently diverge: a future bump to one file
  leaves the other stale, and nothing in CI catches it.

## Suggestion
- Bump both `pyproject.toml:7` and `fourseer/__init__.py:62` to `0.2.0`.
- Add `tests/test_version.py` that parses the `version` field out of
  `pyproject.toml` (via `tomllib` on Python 3.11+, or a minimal regex for
  3.10) and asserts it equals `fourseer.__version__`. This makes the two
  copies a single logical value with a CI guard.
- (Optional, larger) derive `__version__` from the package metadata
  (`importlib.metadata.version("fourseer")`) so there is exactly one source.
