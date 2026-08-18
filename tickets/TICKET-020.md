# TICKET-020: Implement extract_tokens_cost — conservative token/cost extraction

## Title
Add `extract_tokens_cost(trajectory: Trajectory) -> tuple[int | None, float | None]`
to `fourseer/report.py`.

## Evidence
`fourseer/report.py` has no function to extract token counts or cost from a
`Trajectory`. The `Trajectory` dataclass (models.py) carries
`messages: list[dict[str, Any]]` where each message has `role` and `content`.
The README promises "tokens/cost" in the report, but no extraction function
exists.

A full scan of all 44 seed trajectories confirms that NO trajectory contains
structured token or cost data. There is no usage JSON block, no
`prompt_tokens: N` key-value pair, no `total_tokens: N`, no cost figure. The
`Trajectory` JSON files carry only `outcome` and `messages` at the top level.
The seed DOES contain incidental prose: a shell `usage()` function with
`FIVE_MAX_TOKENS=65536`, TypeScript type declarations (`prompt_tokens: number;`),
and the word "usage" in comments — none of which is a real usage record.

## Impact
Without `extract_tokens_cost` the report cannot display token/cost columns. The
function must be conservative: it should only return values when a structured,
unambiguous token/cost record is present in the message content. For the current
seed (and for any trajectory without such records) it must return `(None, None)`.

## Suggestion
In `fourseer/report.py`, add a function `extract_tokens_cost` that scans each
message's `content` for an explicit, unambiguous usage record. Only a line that
is itself a usage record is matched (line-anchored), so incidental prose (a
shell `usage()` function, TS `prompt_tokens: number;` type declarations, the
word "usage" in comments) never matches. Returns `(None, None)` when no such
record is present (the seed case). Pure: no I/O, no mutation.

Marker (conservative, line-anchored, case-insensitive): a line of the form
`usage: tokens=<int> [cost=<float>]`.

- `tokens=<int>` is required; `cost=<float>` is optional.
- Verified: this pattern has 0 hits across all 44 seed trajectories, while a
  loose `usage.*tokens=` has 1 (the shell `usage()` + `FIVE_MAX_TOKENS` span) —
  confirming the line-anchored form is what keeps it conservative.
- If multiple records appear, sum tokens and sum cost (deterministic, in message
  order). If only tokens are present, cost is `None`.
