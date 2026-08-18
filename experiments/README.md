# Experiment artifacts

Optimization and validation measurements for ppm-edge-runtime.

## Layout

- `ppm_edge_combined_variant_experiment_report.md` — main write-up (NamedTuple + int()-removal study)
- `runtime_audit/` — earlier audit + patches
- `validation_raw/` — first validation-phase JSON (variants, cold-start, GC)
- `optimization_raw/` — before/after for the landed NamedTuple change
- `cpython_ext/` — C-extension boundary experiment

## Status

- **Landed:** `Decision` as `typing.NamedTuple`
- **Not merged:** removal of per-call `int()` in `process()` — real speedup (~25–38%), blocked on calling-contract (float truncation). See the combined variant report.

No production code changes in this commit.
