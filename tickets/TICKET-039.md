# TICKET-039: `IssueDrift` value object in models.py

## Title
Add a frozen `IssueDrift` value object to `fourseer/models.py` describing one
closed-in-commits-but-still-open issue (the per-issue row of the drift diff).

## Evidence
`fourseer/models.py` has no drift model. The Drift phase (cycle 9) needs a pure
value object to carry, per drifted issue: the issue number, the commit that
referenced it as closed, that commit's subject, and a stable machine tag.

## Impact
Without the model, `fourseer/drift.py` cannot return structured, comparable,
hashable drift rows, and the package cannot re-export a drift type.

## Suggestion
In `fourseer/models.py`, add a frozen `@dataclass` `IssueDrift` with fields
`issue_no: int`, `commit_hash: str` (the full hash of the first referencing
commit), `commit_message: str` (that commit's subject line), and
`code: str = "closed_but_still_open"` (a stable machine tag). Pure value object;
add it to the module docstring model list.
