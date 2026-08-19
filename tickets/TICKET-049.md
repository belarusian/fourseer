# TICKET-049: `fourseer/cli.py` module is missing (declared but absent)

## Title
Create `fourseer/cli.py` exposing a `main()` entrypoint. The console script is
declared in `pyproject.toml` and documented in `__init__.py`, but the module
does not exist, so the installed `fourseer` command is broken.

## Evidence
- `pyproject.toml:18-19` declares the console script:
  `[project.scripts]` / `fourseer = "fourseer.cli:main"`.
- `fourseer/__init__.py:18` documents the module in the public-surface list:
  `  - fourseer.cli      : the `fourseer` entrypoint`.
- `ls fourseer/` shows no `cli.py` (only `__init__.py`, `drift.py`, `load.py`,
  `models.py`, `parse/`, `report.py`, `taxonomy.py`, `validate.py`).
- `find fourseer -name cli.py` returns nothing.
- `grep -rn "def main" fourseer/` returns nothing — there is no `main` symbol
  anywhere in the package.

## Impact
- `pip install -e .` produces a `fourseer` console script whose target
  (`fourseer.cli:main`) does not resolve; invoking `fourseer` (or
  `fourseer --help`) fails with `ModuleNotFoundError: No module named
  'fourseer.cli'`.
- The README advertises a "Python CLI + library" with three subcommands
  (report / taxonomy / drift); none of them are reachable because the
  entrypoint is absent.
- `fourseer/__init__.py`'s documented public surface is inaccurate (it lists a
  module that does not exist).

## Suggestion
Create `fourseer/cli.py` with a `main(argv: list[str] | None = None) -> int`
that:
- uses `argparse` with a top-level `fourseer` parser and three subparsers
  (`report`, `taxonomy`, `drift`) — see TICKET-050/051/052 for each subcommand's
  wiring;
- takes the AI-artifact directory as a positional (or `--ai-dir`) argument and
  an optional `--repo` path, then calls `load_run(ai_dir, repo_path)`;
- prints the subcommand's rendered block to stdout and returns `0`;
- returns a non-zero exit code (and prints to stderr) on a missing/unreadable
  `ai_dir` or an unreadable git repo (the one case `load_run` raises).
Keep it stdlib-only (`argparse`, `sys`, `pathlib`) and consistent with the
package's pure-library style: `cli.py` is the thin I/O boundary; all analysis
stays in the existing library functions. Add `fourseer/cli.py` to the
`[tool.setuptools] packages` list is NOT needed (it is inside the `fourseer`
package), but do add a `tests/test_cli.py` (see TICKET-050..052) and confirm
`fourseer --help` and each subcommand run against the seed.
