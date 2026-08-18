# Phase 19 — Auth Token Replay / Capability Windows

**Harness-only.** Not a claim against the production C kernel.

## Matrix

| Test | Result |
|------|--------|
| TOKEN_ISSUE_AND_USE | PASS |
| TOKEN_REPLAY | PASS |
| UNKNOWN_FORGED_TOKEN | PASS |
| DOUBLE_SPEND | PASS |
| EPOCH_LIMIT | PASS |
| REAUTH_NO_REPLENISH | PASS |
| REJECTED_NO_CONSUME | PASS |
| BUDGET_EXHAUSTED | PASS |
| PATH_INVARIANTS | PASS |
| RANDOMIZED_TOKEN_OPS (10k) | PASS |

**ALL_PASS = True**

## Invariants held

- One-time tokens; replay rejected; state unchanged
- Forged/unknown tokens rejected without consuming budget
- Rejected ops do not mark tokens used
- Epoch limit bounds updates per reauth window
- Reauth does not replenish path_sum or origin_budget
- path_sum monotonic and ≤ B_global under mixed token ops
