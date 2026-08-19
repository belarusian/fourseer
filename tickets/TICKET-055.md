# TICKET-055: README `## Usage` section is empty

## Title
Fill in the README's `## Usage` section with the three subcommands
(`report`, `taxonomy`, `drift`), their single positional argument, and the
`python -m fourseer` / console-script invocation forms.

## Evidence
`README.md` is 12 lines long. It ends at line 12 with the heading `## Usage`
and nothing beneath it (verified with `cat -A README.md`):

    11  (blank)
    12  ## Usage

The three subcommands are fully implemented and tested in-process
(`fourseer/cli.py`, `tests/test_cli.py`), and the CLI help text is:

    usage: fourseer [-h] {report,taxonomy,drift} ...
      report    per-cycle metrics table
      taxonomy  failure-mode distribution
      drift     plan drift (Build Order vs executed cycles)

Each subcommand takes one positional `ai_dir` (the project AI-artifact
directory). The package is installed as a console script
(`pyproject.toml:23`) and also runnable via `python -m fourseer`
(`fourseer/__main__.py`).

## Impact
A newcomer landing at the repo reads the feature bullets (report / taxonomy /
drift) but has no command to run. The `## Usage` heading promises content that
is absent, so the README is incomplete and the CLI is effectively
undocumented for first-time users.

## Suggestion
Under `## Usage`, document:
- install: `pip install -e .` (dev: `pip install -e ".[dev]"`).
- the two invocation forms: `fourseer <subcommand> <ai-dir>` and
  `python -m fourseer <subcommand> <ai-dir>`.
- one line per subcommand with a short example, e.g.
  `fourseer report <ai-dir>` -> per-cycle metrics table;
  `fourseer taxonomy <ai-dir>` -> failure-mode distribution;
  `fourseer drift <ai-dir>` -> plan drift (Build Order vs executed cycles).
- note that `drift` is plan drift only (issue drift needs a caller-supplied
  open-issue set, per `fourseer/cli.py` docstring).
- note the exit code: `0` on success, `2` when the AI directory is missing or
  not a directory.
