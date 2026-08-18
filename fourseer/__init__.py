"""fourseer — loop intelligence for the four pipeline.

A stdlib-first Python CLI + library that parses autonomous-build loop
artifacts (trajectories JSON, append-only markdown gate log, cycles.out,
git history) and reports per-cycle metrics, a failure-mode taxonomy, and
drift (issue drift + plan drift).

Public surface is re-exported here; submodules:
  - fourseer.parse      : artifact parsers
  - fourseer.report     : per-cycle metrics
  - fourseer.taxonomy   : failure-mode classification
  - fourseer.drift      : issue + plan drift detection
  - fourseer.cli        : the `fourseer` entrypoint
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
