# PPM Edge Runtime — Competition Summary

**Repository:** [prioritizedprotection086/Ppm_edge_runtime](https://github.com/prioritizedprotection086/Ppm_edge_runtime)  
**Production audit:** Phase 20 on commit recorded in `phase20_production_trace_audit/PHASE_20_RESULTS.json`

---

## 1. Problem

Wearables and edge devices need **local, bounded decisions** on sensitive signals without shipping raw biometrics to the cloud. Requirements: deterministic behavior, low latency, minimal state, explicit priority handling, and a clear protection flag for downstream actuators or policies.

## 2. PPM Edge solution

A tiny dual-language **decision kernel**:

- **C** (`Src/Ppm_edge.c`) for embedded deployment  
- **Python** (`src/ppm_edge/runtime.py`) as a behaviorally aligned reference for tests and integration  

Each sample yields a decision: value, absolute delta from last value, protected flag, confidence, priority.

## 3. Architecture

```
Sensor → InputSample / ppm_input_t
           → PPM process (threshold + priority)
           → Decision / ppm_output_t
           → Device / edge AI / outer safety policy
```

State retained: baseline, last value, threshold, initialized/protection/confidence/priority flags. No biometric archive; no required network.

## 4. Verified production capabilities (Phase 20)

| Capability | Production |
|------------|------------|
| Threshold protection | Yes |
| CRITICAL priority forces protection | Yes |
| Reset to baseline | Yes |
| C ↔ Python decision consistency (shared traces) | Yes |
| ASan/UBSan clean run of production C + trace driver | Yes |

| Capability | Production |
|------------|------------|
| Global path budget `B_global` | **No** |
| Origin budget | **No** |
| Checkpoints / recovery MAC | **No** |
| Re-authentication | **No** |
| Atomic CAS budget accounting | **No** |

## 5. Test methodology

1. **Python unit tests** — `tests/` via pytest  
2. **CMake** — static library + `ppm_demo`  
3. **Phase 20** — deterministic traces: threshold±1, zero delta, ±deltas, INT32 extremes, repeated samples, reset, CRITICAL, negative threshold, 10 000 random samples; identical traces in C driver with ASan+UBSan; Python/C compare  

Harness FormalPolicy was **not** used as a stand-in for production.

## 6. Phase 20 results

- **ALL_PASS=True**, **failures=0**  
- Matrix: THRESHOLD_BOUNDARIES, ZERO_DELTA, POS_NEG_DELTAS, INT32_EXTREMES, REPEATED, RESET, CRITICAL_PRIORITY, NEGATIVE_THRESHOLD, LONG_RANDOMIZED, C_CMAKE_AND_SANITIZERS, PYTHON_C_IDENTICAL_TRACES — all **PASS**  
- Artifacts: `research/phase20_production_trace_audit/`

## 7. Harness research results (Phases 13–19)

Exploratory **policy-layer** designs (path budget, origin budget, checkpoints, tokens, interleavings) under `research/phase14+`. Useful for future product policy modules; **not** claims about the shipping kernel.

## 8. Performance / latency

`experiments/` contains Python microbenchmark JSON (e.g. NamedTuple decision path, ns-scale process times on a shared host). Treat as **indicative host measurements**, not formal embedded SLAs. No competition claim of production latency targets beyond “designed for ultra-low latency / minimal state.”

## 9. Limitations

- Protection is **threshold + priority**, not cumulative path or spatial policy  
- No built-in checkpoint/reauth  
- Python `abs(INT32_MIN)` is 2³¹; C uses int64 intermediate and `uint32` delta — Phase 20 requires protection/value match; delta may differ on extremes  
- Research harness must not be confused with production  

## 10. Reproducibility

```bash
git clone https://github.com/prioritizedprotection086/Ppm_edge_runtime.git
cd Ppm_edge_runtime

# Python
PYTHONPATH=src pytest -q

# C
cmake -S . -B build && cmake --build build && ./build/ppm_demo

# Sanitizers + Phase 20
gcc -std=c11 -Wall -Wextra -g -O1 \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -ISrc Src/Ppm_edge.c \
  research/phase20_production_trace_audit/c_trace_driver.c \
  -o /tmp/ppm_c_trace_asan
ASAN_OPTIONS=detect_leaks=0 /tmp/ppm_c_trace_asan

cd research/phase20_production_trace_audit
PPM_REPO=$(git rev-parse --show-toplevel 2>/dev/null; pwd)/../..  # or set to repo root
# From repo root:
PPM_REPO=$PWD python3 research/phase20_production_trace_audit/phase20_production_trace_audit.py
```

## 11. Future work

- Optional outer **policy layer** (path budget, origin authority) if product requires it — keep kernel frozen  
- Formal embedded latency benches on target MCUs  
- Document INT32 delta contract across FFI boundaries  

---

*Production claims above are limited to Phase 20–verified behavior on main.*
