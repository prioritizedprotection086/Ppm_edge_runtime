# CPython C-Extension Boundary Benchmark

## What this measures

A minimal CPython extension module (`benchmark/cext/ppm_edge_ext.c`) that exposes
`ppm_process()` directly through the Python C API — `PyArg_ParseTuple` /
`Py_BuildValue`, no `ctypes.Structure` marshalling anywhere in the call path. The
runtime state (`ppm_runtime_t`) is embedded inline in the extension object's memory
block. It `#include`s `Src/Ppm_edge.h` and links `Src/Ppm_edge.c` unmodified — same
production kernel source as every other layer in this benchmark family.

**`Src/Ppm_edge.c` and `Src/Ppm_edge.h` were not modified.** Verified by `diff`
against the uploaded originals immediately before and after this work (identical,
md5 unchanged). No production algorithm behavior was changed.

All three layers below were built and run back-to-back, in the same process/machine
session, using the same deterministic input generator (`benchmark/inputs.py`) and
the same seeds (401–405) as the isolated-C benchmark, so the comparison isn't
confounded by different hardware or a different point in time.

## Methodology

- 5 independent trials, seeds `[401, 402, 403, 404, 405]`
- 5,000 warmup ops (untimed) + 1,000,000 measured ops per trial, all three layers
- Isolated C: each call timed individually with `clock_gettime(CLOCK_MONOTONIC)`
- CPython extension / pure Python: each call timed individually with
  `time.perf_counter_ns()`
- Percentiles (p50/p95/p99/p99.9/max/mean) via `numpy.percentile`, identical
  methodology across all three layers and consistent with the earlier isolated-C
  and competitive-baseline reports

**Caveat on timer overhead:** the isolated-C loop calls `clock_gettime` directly in
C; the Python-level loops call `time.perf_counter_ns()` from Python bytecode, which
itself costs on the order of tens of nanoseconds per call. That per-call timer
overhead is included in the "cext" and "pure_python" numbers below but not in
"isolated C." At the isolated-C layer's ~32ns median this would matter; at the
cext layer's ~500ns and pure-Python's ~2,200ns medians it's a small fraction and
doesn't change the qualitative comparison, but it means the true call-only cost of
the extension layer is very slightly lower than reported.

## Results (mean across 5 trials, nanoseconds unless noted)

| Metric | Isolated C | CPython extension | Pure Python PPMRuntime |
|---|---:|---:|---:|
| p50 | 32.0 | 501.8 | 2,237.0 |
| p95 | 37.2 | 612.0 | 2,654.8 |
| p99 | 48.2 | 918.0 | 5,134.2 |
| p99.9 | 106.6 | 3,854.4 | 20,030.8 |
| max | 299,478.6 | 2,999,773.2 | 3,196,650.4 |
| mean | 34.4 | 536.9 | 2,389.8 |
| throughput (ops/s) | 14,146,701 | 1,355,458 | 383,197 |

(`max` and to a lesser extent `p99.9` are noisy across trials — driven by OS
scheduling jitter/page faults, not the kernel logic — see stdev in the raw JSON.)

## Overhead: CPython extension vs. isolated C

At the mean: **~503ns of added overhead per call, ~15.6x isolated-C latency**
(536.9ns vs 34.4ns). At p50: ~470ns added, ~15.7x. This is the CPython call
boundary cost — `PyArg_ParseTuple` unpacking, `Py_BuildValue` tuple construction
and the associated object allocations, plus normal Python interpreter dispatch
overhead to reach the C call — on top of an ~32–48ns kernel call that itself does
almost nothing (a few branches and one subtraction).

Throughput: isolated C sustains ~14.1M ops/s; the extension sustains ~1.36M ops/s,
about **9.6% of isolated-C throughput (≈10.4x slower)**.

## CPython extension vs. pure Python PPM runtime

The extension is faster than the pure Python reference at every percentile
measured: **~4.3–5.6x lower latency depending on percentile** (4.46x at p50, 4.45x
at mean, up to 5.6x at p99), and **~3.54x higher throughput** (1.36M ops/s vs
383K ops/s).

## Three-layer summary

```
isolated C            :  34.4 ns/op   14.1M ops/s   (baseline)
CPython C extension   : 536.9 ns/op   1.36M ops/s   ~15.6x slower than isolated C
                                                      ~4.4x faster than pure Python
pure Python PPMRuntime: 2389.8 ns/op   383K ops/s    ~69.4x slower than isolated C
```

No superiority claims beyond what these numbers directly support: the extension
meaningfully closes part of the gap to the isolated-C ceiling relative to pure
Python, but the CPython call boundary itself — not the kernel logic — remains the
dominant cost at this layer, consuming roughly 94% of the extension's per-call
time.

## Correctness gates re-run after this work

- 400,000-step property test: **0 failures**
- 7,500-step C/Python differential test: **0 mismatches**
- New 3-way differential test (Python reference vs. ctypes C kernel vs. CPython
  extension, same 7,500-step stream): **0 mismatches**
- 16/16 existing test suite: **16 passed**

## Files

- `benchmark/cext/ppm_edge_ext.c` — the extension source
- `benchmark/cext/setup.py` — build script (compiles against unmodified `Src/Ppm_edge.c`)
- `benchmark/cext/differential_test_ext.py` — 3-way correctness check
- `benchmark/cext/bench_layers.py` — extension + pure-Python benchmark harness
- `benchmark/cext/results/cext_and_python_layers_summary.json` — raw per-trial and aggregate data
- `benchmark/c_bench/results/isolated_c_summary.json` — isolated-C layer data (re-run fresh, same session)
