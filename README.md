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
research/              Harness-only security & policy research phases
.github/workflows/     CI
```

Production runtime code lives under `src/` and `Src/`.
`experiments/` and `research/` are **not** linked into production builds.

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

See [`research/PHASES.md`](research/PHASES.md). Recent harness phases (14–19) study global path budgets, accounting invariants, checkpoint integrity, and auth-token replay. **Harness-only — production kernel unchanged.**

## License

All rights reserved — no license granted (see `Project.toml`).
