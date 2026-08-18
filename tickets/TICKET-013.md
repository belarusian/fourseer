# TICKET-013: Exactly ONE real-seed test for `validate_run`

## Title
Add exactly one seed-backed test that runs `validate_run(load_run(seed_dir))`
and asserts the exact set of issue codes it produces.

## Evidence
The cycle constraints require exactly ONE real-seed test (using the
`seed_dir` fixture) that asserts the set of issue codes `validate_run`
produces on the seed. The seed is expected to be internally consistent OR to
have a small, stable, documented set of issues — we assert that exact set.

## Derived expected seed result
Running the cross-checks against the seed (cycles.out cycles 7-28; gate-log
blocks 1-20 and 23-28; Build Order ranges 1-3,4-6,7-9,10-13,14-17,18-20;
referenced trajectory basenames all present among the 44 files):

- `orphan_trajectory_path`: **none** (every referenced basename exists)
- `cycle_not_in_gate_log`: cycles **21, 22** (in cycles.out, no gate block)
- `gate_cycle_not_in_cycles_out`: cycles **1, 2, 3, 4, 5, 6** (gate block, no
  cycles.out record)
- `build_order_range_gap`: cycles **21, 22, 23, 24, 25, 26, 27, 28** (executed
  outside any planned range)

Total: 16 issues. The set of distinct codes is
`{cycle_not_in_gate_log, gate_cycle_not_in_cycles_out, build_order_range_gap}`.

## Impact
This test pins the validator's behavior on the real dataset and documents the
seed's known inconsistencies, so a future parser change that silently alters
the cross-checks is caught.

## Suggestion
In `tests/test_validate.py`, add one test using the `seed_dir` fixture:

```python
def test_seed_validate(seed_dir):
    run = load_run(seed_dir)
    issues = validate_run(run)
    codes = {i.code for i in issues}
    assert codes == {
        "cycle_not_in_gate_log",
        "gate_cycle_not_in_cycles_out",
        "build_order_range_gap",
    }
    # exact per-code cycle sets
    assert {i.cycle_no for i in issues if i.code == "cycle_not_in_gate_log"} == {21, 22}
    assert {i.cycle_no for i in issues if i.code == "gate_cycle_not_in_cycles_out"} == {1, 2, 3, 4, 5, 6}
    assert {i.cycle_no for i in issues if i.code == "build_order_range_gap"} == {21, 22, 23, 24, 25, 26, 27, 28}
    assert not any(i.code == "orphan_trajectory_path" for i in issues)
```

## Tests
This ticket IS the test.
