# Phase 20 — Production Trace Audit

**Commit:** `55d1cdb08706e0b063e7f55e7c212a11f24538b8` (main)  
**Repo:** prioritizedprotection086/Ppm_edge_runtime  
**Scope:** Production C (`Src/Ppm_edge.c`) + Python (`src/ppm_edge/runtime.py`) only.  
**FormalPolicy harness was not used as a substitute.**

## A. Actual production findings

### Security property flags

| Flag | Value | Evidence |
|------|-------|----------|
| PRODUCTION_HAS_GLOBAL_PATH_BUDGET | **FALSE** | No `path_sum`/`B_global` in `Src/Ppm_edge.c`, `.h`, or `runtime.py`. `ppm_process` always accepts and updates `last_value`. |
| PRODUCTION_HAS_ORIGIN_BUDGET | **FALSE** | `ppm_runtime_t` / `RuntimeState` have no origin budget fields (`Src/Ppm_edge.h`, `runtime.py`). |
| PRODUCTION_HAS_CHECKPOINTS | **FALSE** | Public API is only `ppm_init`, `ppm_reset`, `ppm_process`, `ppm_version` (`Src/Ppm_edge.h`). |
| PRODUCTION_HAS_RECOVERY | **FALSE** | `ppm_reset` / `reset()` only restore `last_value` to baseline — not checkpoint recovery. |
| PRODUCTION_HAS_REAUTH | **FALSE** | No session/epoch/token APIs in header or Python module. |
| PRODUCTION_HAS_ATOMIC_BUDGET_ACCOUNTING | **FALSE** | No CAS/version/budget accounting in `ppm_process`. |

### What production does implement

- Threshold protection: `delta >= threshold` → `protected`
- `PPM_PRIORITY_CRITICAL` / `Priority.CRITICAL` forces protected
- `last_value` + baseline state
- Negative threshold clamped to 0
- Confidence 100/75/50
- C: int32 signals, abs delta via int64 intermediate

### Behavioral tests (executed)

All **PASS**: threshold ±1, zero delta, ±deltas, INT32 min/max/span, repeated, reset, critical, negative threshold, 10 000 randomized samples, CMake `ppm_demo`, ASan+UBSan driver, Python↔C identical traces (value/protection; int32 delta may differ Python unlimited vs C `uint32`).

## B. Harness-only (Phases 13–19)

`B_global`, origin budget, checkpoints, reauth, and concurrent CAS races live under `research/phase14+` only. They are **not** production mechanisms and do not imply production vulnerabilities or guarantees.

## C. Unsupported claims

Any claim that main-branch production enforces global path budget, origin budget, checkpoint integrity, recovery-as-policy, reauth, or atomic budget accounting is **unsupported** by source evidence.

## PASS/FAIL matrix

All listed production tests: **PASS**. `ALL_PASS=True`, `failures=0`.
