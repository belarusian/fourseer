"""Allow ``python -m fourseer`` to invoke the CLI.

Delegates to :func:`fourseer.cli.main`, so ``python -m fourseer <subcommand>
<ai-dir>`` behaves identically to the installed ``fourseer`` console script.
"""

from __future__ import annotations

from fourseer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
