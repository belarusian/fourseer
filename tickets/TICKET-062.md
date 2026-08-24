# TICKET-062: Fix mypy union-attr error in report.py

**Date:** 2026-08-24  
**Priority:** High (gate failure)  
**Assignee:** (to be assigned)

## Problem

mypy fourseer/ --ignore-missing-imports reports a union-attr error on line 188 of fourseer/report.py:

fourseer/report.py:188: error: Item "None" of "list[CycleClassification] | None" has no attribute "__iter__" (not iterable)  [union-attr]

The error occurs because has_class = classifications is not None is a boolean that mypy can't use for type narrowing, so when classifications is used in the for loop, mypy still considers it potentially None.

## Solution

Replace the has_class boolean with direct type narrowing:

Before (broken):
has_class = classifications is not None
# ...
if has_class:
    for c in classifications:  # mypy flags this as potentially None
        ...

After (fixed):
if classifications is not None:
    for c in classifications:  # mypy knows classifications is list[CycleClassification]
        ...

This is a pure stdlib fix; no new dependencies.

## Acceptance Criteria

- mypy fourseer/ --ignore-missing-imports reports no errors
- pytest tests/ -x -q passes
- ruff check fourseer/ passes
- Code squashed to a single commit
- PR merged with --merge --delete-branch
- GitHub issue closed

## Notes

- The fix is minimal and focused on the specific mypy error.
- The change preserves the existing logic; only the type narrowing mechanism is altered.
