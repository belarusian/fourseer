# TICKET-054: CLI end-to-end subprocess test is missing

## Title
Add a subprocess-based end-to-end test that invokes the real CLI entrypoints
(`python -m fourseer` and the `fourseer` console script), not just the
in-process `main()` function.

## Evidence
`tests/test_cli.py` imports the function and calls it directly:
- `tests/test_cli.py:22` `from fourseer.cli import main`
- every test calls `main([...])` in-process, e.g. `tests/test_cli.py:88`
  `rc = main(["report", str(ai_dir)])` and `tests/test_cli.py:150`
  `assert main(["report", str(seed_dir)]) == 0`.

No test ever spawns the CLI as a subprocess. The two real entrypoints a user
runs are therefore untested:
- `fourseer/__main__.py` (7 lines) — `python -m fourseer` — delegates to
  `fourseer.cli.main` and is never exercised by any test.
- the console script declared at `pyproject.toml:23`
  (`[project.scripts] fourseer = "fourseer.cli:main"`).

Verified manually that the entrypoints work today:
`python3 -m fourseer report /home/sasha/AI/fourseer/seed` -> returncode 0,
stdout begins `# Per-Cycle Metrics (22 cycles)`.

## Impact
The in-process tests prove the function logic but not the actual entrypoints.
A regression in `__main__.py`, the console-script wiring, argparse `prog`
naming, or exit-code propagation (e.g. the `_MISSING_DIR_EXIT = 2` path in
`fourseer/cli.py:54`) would ship undetected, because no test observes the
process boundary (argv parsing, stdout/stderr separation, real exit code).

## Suggestion
Add `tests/test_cli_subprocess.py` using
`subprocess.run([sys.executable, "-m", "fourseer", <subcommand>, str(ai_dir)],
capture_output=True, text=True, cwd=<repo root>)`.
- Assert `returncode == 0` and the expected stdout header for each of the
  three subcommands (`report` / `taxonomy` / `drift`).
- Assert the missing-dir path returns a non-zero code with the error on
  stderr and empty stdout (mirrors `fourseer/cli.py:108-114`).
- Reuse the inline `ai_dir` fixture (factor it into `tests/conftest.py` or
  import `_write_ai_dir` from `test_cli`).
- Add exactly ONE real-seed subprocess test gated on the `seed_dir` fixture,
  pinning the verified slice (`# Per-Cycle Metrics (22 cycles)`).
