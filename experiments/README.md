# Experiments

Optimization and validation measurements against the production-shaped Python/C runtime.

| Path | Contents |
|------|----------|
| `ppm_edge_combined_variant_experiment_report.md` | NamedTuple + `int()`-removal study |
| `optimization_raw/` | Before/after for NamedTuple change |
| `validation_raw/` | Variant benches, cold-start, GC |
| `runtime_audit/` | Audit report + patches |
| `cpython_ext/` | C-extension boundary experiment |

Production code changes are only those already merged in `src/` / `Src/`.
