# PPM Edge Runtime

Deterministic, ultra-low-latency local decision kernel for privacy-preserving adaptive regulation on wearables, edge AI, and resource-constrained devices.

> Process sensitive signals locally, make a bounded decision locally, and retain as little information as possible.

## Design goals

- Deterministic execution, ultra-low latency
- Minimal memory and persistent storage
- Local-first; no required cloud or biometric archive
- Explicit priority handling and bounded adaptive regulation
- Easy integration with sensors and edge-AI pipelines

## Repository layout

```
src/ppm_edge/          Python reference implementation
Src/                   C kernel (Ppm_edge.c / Ppm_edge.h)
Examples/              C demo
tests/                 Python tests
experiments/           Optimization / validation measurements
research/              Research phases + production audit (Phase 20)
.github/workflows/     CI
```

Production runtime code lives under `src/` and `Src/`.  
`experiments/` and most of `research/` are **not** linked into production builds.

---

## Competition / evaluation (verified production only)

This section describes **only** capabilities that exist in the main-branch C and Python runtime and that were re-checked in **Phase 20** (`research/phase20_production_trace_audit/`).

### What production implements

| Capability | Status |
|------------|--------|
| Threshold-based protection (`delta >= threshold` → protected) | Yes |
| CRITICAL priority forces protection | Yes |
| `last_value` + baseline state | Yes |
| `ppm_reset` / `reset()` (restore last value to baseline) | Yes |
| Confidence bands (100 / 75 / 50) | Yes |
| Dual C + Python reference with matching decision semantics | Yes (Phase 20 identical-trace audit) |

### What production does **not** implement

These appear only in harness research (Phases 13–19), **not** in `Src/` or `src/ppm_edge/`:

- Global path budget (`B_global` / `path_sum`)
- Origin budget
- Checkpoints / MAC recovery
- Re-authentication / session epochs
- Compare-and-swap atomic budget accounting

See [`research/COMPETITION_SUMMARY.md`](research/COMPETITION_SUMMARY.md) and [`research/phase20_production_trace_audit/PHASE_20_REPORT.md`](research/phase20_production_trace_audit/PHASE_20_REPORT.md).

### Reproducible commands

```bash
# Python unit tests
PYTHONPATH=src pytest -q

# CMake build + demo
cmake -S . -B build && cmake --build build
./build/ppm_demo

# ASan + UBSan production trace driver (Phase 20)
gcc -std=c11 -Wall -Wextra -g -O1 \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -ISrc Src/Ppm_edge.c \
  research/phase20_production_trace_audit/c_trace_driver.c \
  -o /tmp/ppm_c_trace_asan
ASAN_OPTIONS=detect_leaks=0 /tmp/ppm_c_trace_asan

# Full Phase 20 production audit
cd research/phase20_production_trace_audit
PPM_REPO=$(git rev-parse --show-toplevel) python3 phase20_production_trace_audit.py
```

---

## Quick start (Python)

```bash
PYTHONPATH=src pytest -q
```

## Quick start (C)

```bash
cmake -S . -B build && cmake --build build
./build/ppm_demo
```

## Research phases

| Area | Location | Note |
|------|----------|------|
| Production audit | `research/phase20_production_trace_audit/` | Verified against main |
| Harness policy (14–19) | `research/phase14/` … `phase19/` | **Not** in production kernel |
| Index | [`research/PHASES.md`](research/PHASES.md) | |

## License

All rights reserved — no license granted (see `Project.toml`).
