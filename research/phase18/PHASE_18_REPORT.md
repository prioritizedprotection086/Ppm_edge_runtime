# Phase 18 — Checkpoint / State Serialization Integrity

**Harness-only.** Does **not** claim findings against the production C kernel.  
Builds on Phase 17-style hardened recovery model (`hardened_policy.py`).

**B_global = 50_000**

## Matrix

| Attack | Result |
|--------|--------|
| FORGED_PATH_SUM | PASS |
| FORGED_ORIGIN_BUDGET | PASS |
| FORGED_SESSION_ID | PASS |
| FORGED_ORIGIN | PASS |
| FORGED_VALUE | PASS |
| OLD_CHECKPOINT_REPLAY | PASS |
| CROSS_SESSION_CHECKPOINT | PASS |
| MALFORMED_CHECKPOINTS | PASS |
| SERIALIZATION_ROUND_TRIP | PASS |
| RANDOMIZED_TAMPERING (10k, seed=18) | PASS |

**ALL_PASS = True**

## Hardened recovery rules exercised

- MAC integrity over security fields
- `path_sum` cannot decrease via recovery (blocks old checkpoint replay)
- `origin_budget` cannot increase via recovery
- `session_id` must match (blocks cross-session)
- Malformed / wrong-type checkpoints rejected with **no partial state update**
- Valid JSON round-trip restores identical security counters

## Artifacts

- `hardened_policy.py` — Phase 17-style model
- `phase18_state_integrity.py`
- `PHASE_18_RESULTS.json`
