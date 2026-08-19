# TICKET-044: `PlanDrift` value object in models.py

## Title
Add a frozen `PlanDrift` value object to `fourseer/models.py` describing one
cycle that drifted from the Build Order plan (the per-cycle row of the plan-drift
diff).

## Evidence
`fourseer/models.py` has `IssueDrift` (cycle 9) but no plan-drift model. The
Drift phase (cycle 10) needs a pure value object to carry, per drifted cycle:
the cycle number, the drift direction (a closed `status` set), and a stable
machine tag.

## Impact
Without the model, `fourseer/drift.py` cannot return structured, comparable,
hashable plan-drift rows, and the package cannot re-export a plan-drift type.

## Suggestion
In `fourseer/models.py`, add a frozen `@dataclass` `PlanDrift` with fields
`cycle_no: int`, `status: str` (a stable machine tag from the closed set
`"executed_not_planned"` / `"planned_not_executed"`), and
`code: str = "plan_drift"` (a stable machine tag). Document the closed `status`
set in the docstring. Pure value object; add it to the module docstring model
list.
