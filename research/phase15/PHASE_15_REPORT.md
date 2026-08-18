# Phase 15 — Adversarial Budget / Accounting Invariants

**Harness-only. Production kernel FROZEN.**  
**B_global = 100_000**

## Matrix

| Test | Result |
|------|--------|
| EXACT_BOUNDARY | PASS |
| OVERSHOOT | PASS |
| REJECTED_MOVE_ACCOUNTING | PASS |
| ORIGIN_UPDATE_LOOP | PASS |
| REAUTH_LOOP | PASS |
| RECOVERY_LOOP | PASS |
| INTEGER_EDGE_VALUES | PASS |
| ORIGIN_AND_PATH_COMBINATION | PASS |
| RANDOMIZED_SEQUENCE (10k, seed=42) | PASS |
| STATE_CONSISTENCY | PASS |

**ALL_PASS = True** (0 failures recorded)

## Invariants held

- `0 <= path_sum <= B_global` after every operation
- `path_sum` never decreases
- Origin updates / re-auth / recovery never replenish budget
- Rejected moves do not change accounting core (path, origin, last_accepted, accept counts)
- Arithmetic edge values cannot force `path_sum > B_global`

## Artifacts

- `phase15_budget_invariants.py`
- `formal_policy_bglobal.py` (from Phase 14)
- `PHASE_15_RESULTS.json`
