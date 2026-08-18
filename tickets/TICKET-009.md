# TICKET-009: Add frozen `ConsistencyIssue` value object to `fourseer/models.py`

## Title
Add a frozen `ConsistencyIssue` dataclass to the models module: a pure value
object describing one cross-source inconsistency found by the validator.

## Evidence
`fourseer/models.py` currently defines `Trajectory`, `CycleRecord`,
`BuildOrderRow`, `CycleBlock`, `GateLog`, `CommitRecord`, and `Run`. There is no
type to represent a *mismatch* between the four independently-parsed sources.
The consistency layer (TICKET-011) needs a stable, hashable, comparable value
object it can return in a deterministic list.

## Impact
Without a dedicated type, `validate_run` would have to return ad-hoc dicts or
tuples, losing self-documentation, type safety (mypy), and a stable sort key.
The Report/Taxonomy/Drift phases (cycles 4-10) will consume these issues, so a
first-class model is required now.

## Suggestion
In `fourseer/models.py`, add:

```python
@dataclass(frozen=True)
class ConsistencyIssue:
    code: str            # stable machine tag, e.g. "orphan_trajectory_path"
    cycle_no: int | None # the cycle the issue concerns, or None
    detail: str          # human-readable explanation
```

- `code` is a stable machine tag (snake_case).
- `cycle_no` is `None` when the issue is not tied to a single cycle.
- `detail` is a free-text, deterministic explanation.
- Frozen (immutable) so instances are hashable and safe to sort/dedupe.
- Document the canonical set of `code` values in the docstring.

## Tests
`tests/test_models.py`: construct a `ConsistencyIssue`, assert field values,
assert frozen-ness (mutation raises `FrozenInstanceError`), and that two
identical instances compare equal and hash equal.
