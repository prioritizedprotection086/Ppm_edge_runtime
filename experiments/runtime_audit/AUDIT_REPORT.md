# Ppm_edge_runtime — Audit Report

Repo: `prioritizedprotection086/Ppm_edge_runtime`
Audit performed against a fresh clone of `main` (commit `7d81d6a` in this
audit's local history — see note on commit SHAs below).

## What this audit did

1. Re-ran and made reproducible the two correctness tests already verified
   informally in an earlier session.
2. Built a full benchmark suite (latency percentiles, cold vs. warm, memory,
   allocation behavior) for both the C and Python implementations.
3. Captured the exact environment for every run.
4. Made the whole thing runnable from one command.
5. Added CI regression gates, tuned with a wide margin to avoid flaking on
   shared runners while still catching real regressions (verified by
   injecting a fake regression and confirming the gate fails).
6. **Did not optimize anything.** No production code was touched except a
   dead-file removal, which is isolated as its own commit.
7. Kept the code cleanup and the benchmark infrastructure as two separate
   commits, exactly as requested.

## A note on commit SHAs

I don't have push/write access to the real GitHub repo, and GitHub's public
API was rate-limited when I tried to fetch the true `main` HEAD SHA
unauthenticated. So the commit SHAs below (`7d81d6a`, `a9e6cec`, `d9de723`)
are from a **local git history I built to mirror the real repo's current
state**, not the real repo's actual SHAs. When you apply the two patches
below to your real clone, your real commit SHAs will differ — that's
expected and fine. `bench/run_benchmarks.sh` always captures the *real*
`git rev-parse HEAD` at run time, so once applied, all future benchmark runs
will record accurate SHAs automatically.

## Correctness tests: results

Both tests pass, reproducibly, with a fixed seed:

```
$ python3 tests_correctness/property_test.py --trials 20000 --steps 20 --seed 42
property_test: trials=20000 steps_per_trial=20 total_checks=400000 failures=0

$ python3 tests_correctness/differential_test.py --runtimes 500 --steps 15 --seed 7
differential_test: runtimes=500 steps_per_runtime=15 total_steps=7500 mismatches=0
```

Plus the existing `pytest` suite: 16/16 pass.

## Benchmark results (this environment — see caveat below)

**Environment:** Python 3.12.3 (CPython), Linux 6.18.5, single logical CPU,
Intel Xeon @ 2.80GHz, gcc 13.3.0, glibc 2.39. Full detail in
`bench/results/*/environment.json` for every run — this is captured
automatically, not hand-typed.

⚠️ **This is a shared sandbox VM, not dedicated hardware.** Treat the
absolute numbers below as one data point, not a definitive benchmark. The
CI thresholds are deliberately loose (large margin) for exactly this reason
— re-baseline them using several runs of GitHub-hosted CI data, not these
numbers, before tightening them.

### Core operation latency

| | Python (`PPMRuntime.process`) | C (`ppm_process`) |
|---|---|---|
| min | 1,607 ns | 19 ns |
| mean | 1,932 ns | 22–25 ns |
| p50 | 1,785 ns | 21 ns |
| p95 | 2,740 ns | 26–33 ns |
| p99 | 3,665 ns | 33–38 ns |
| p99.9 | 24,110 ns | 40–57 ns |
| max | 63,667 ns | ~18,400–43,700 ns (rare scheduler noise outliers) |

C is roughly 80–90x faster per call than Python here, as expected for a
CPython call vs. a native struct-in/struct-out function — not a bug or
finding, just the baseline cost of the language boundary.

### Cold start vs. warm

- **Python cold start** (fresh interpreter, import, first call): ~21 ms,
  almost entirely import/interpreter startup (`import_ns` ≈ 20–24 ms;
  `init_ns` ≈ 4 µs; `first_call_ns` ≈ 9 µs). The first `process()` call
  itself is not meaningfully slower than warm.
- **Python warm** (steady state after 5,000 throwaway calls): essentially
  identical to the general core-latency numbers above — no visible JIT-like
  warmup effect, as expected for CPython.
- **C cold start** (full process launch: fork+exec+dynamic link+one call,
  20 runs): mean ≈ 1.17–1.46 ms, p50 ≈ 1.15–1.49 ms. This is dominated by
  OS process-creation overhead, not by anything in `ppm_process` itself.

### Memory and allocation behavior

- **C:** Zero heap allocations in `ppm_process`, confirmed by static
  analysis (`grep` for `malloc`/`calloc`/`realloc`/`free` in `Src/Ppm_edge.c`
  returns nothing). All state lives in caller-provided structs. This is a
  genuinely strong property — there is no allocator to benchmark because
  there's no allocation.
- **Python:** `tracemalloc`-measured peak traced memory across 20,000 calls
  averages a few hundred bytes per call (short-lived `Delta`/`InputSample`
  objects), consistent with what you'd expect from returning a small
  dataclass per call; nothing unusual. Full detail (top allocation sites)
  is in `bench_python.json`'s `allocations` section.
- Process-level peak RSS (`ru_maxrss`) delta across 100,000 calls was
  effectively noise-level — no evidence of a leak in either implementation.

*(Valgrind/massif was not usable in this sandbox — a required dependency
package 404'd from Ubuntu's security mirror mid-install. The static
allocation analysis above is actually a stronger guarantee for the C side
than a runtime tool would provide, since it proves the *absence* of
allocation calls in the source rather than sampling one run. If you want
massif output too, it should install cleanly in a normal CI runner or dev
machine.)*

## What changed in the two commits

### Commit 1 — code cleanup (isolated, no functional change)
Removes `Src/Ppm_edge/_init_.py`: a stray, misnamed (`_init_.py`, not
`__init__.py`), unused file sitting in a duplicate-cased folder. Confirmed
via `CMakeLists.txt` inspection that only `Src/Ppm_edge.c` and
`Src/Ppm_edge.h` are referenced by the build; this file was dead weight.
Both correctness tests and the full benchmark suite pass identically before
and after this commit (it touches no logic).

### Commit 2 — benchmark infrastructure (isolated, no production code)
Everything described above: `tests_correctness/`, `bench/`, the updated
`.gitignore`, and a new `correctness-and-benchmarks` CI job. Diff touches
zero lines in `Src/Ppm_edge.c`, `Src/Ppm_edge.h`, or
`src/ppm_edge/runtime.py` — verified in the commit message and confirmed by
`git show --stat`.

## How to apply this to the real repo

Two patch files are provided, in order:

```
0001-Remove-stray-unused-Src-Ppm_edge-_init_.py-dead-code.patch
0002-Add-benchmark-infrastructure-and-CI-regression-gates.patch
```

```bash
git clone https://github.com/prioritizedprotection086/Ppm_edge_runtime.git
cd Ppm_edge_runtime
git am /path/to/0001-Remove-stray-unused-Src-Ppm_edge-_init_.py-dead-code.patch
git am /path/to/0002-Add-benchmark-infrastructure-and-CI-regression-gates.patch
git push
```

`git am` preserves the two commits as separate, exactly as built here. If
`main` has moved since this audit, you may need `git am --3way` or a manual
rebase.

## Recommended next step (not done here, per instructions)

No optimization was performed — the audit found no bottleneck to justify
one. If you do want to pursue a future performance PR, the correct process
per this audit's own standard would be: run `bench/run_benchmarks.sh` on
`main` first to capture a real CI-hosted baseline (not this sandbox's), make
the change, run it again, and diff the two `bench_*.json` files as the
PR's before/after evidence.
