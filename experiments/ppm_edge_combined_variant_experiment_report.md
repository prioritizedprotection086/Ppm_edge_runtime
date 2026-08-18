# ppm_edge — Combined-Optimization Experiment (validation only, NOT merged)

**Starting point:** commit `5fe3e0c` (`perf: replace Decision dataclass with NamedTuple`) — current production state.
**Variant under test:** same tree, plus one additional isolated change — the redundant per-call `int()` coercions in `process()` removed. `Decision` remains `typing.NamedTuple` (already in production). Nothing else touched.

```diff
-        value = int(sample.value)
-        threshold = max(0, int(sample.threshold))
+        value = sample.value
+        threshold = sample.threshold
+        if threshold < 0:
+            threshold = 0
```

`__init__`/`reset()` still call `int()` — those run once per runtime lifetime, not per event, and were left alone. **No production file was modified. Nothing was committed.** This is a scratch-copy experiment per your instruction to review results first.

---

## Benchmark: 5 paired trials, same seeds/methodology as the prior before/after comparison (123–127, 100,000 iter + 5,000 warmup)

| metric | current (NamedTuple only) | variant (NamedTuple + no int()) | Δ |
|---|---:|---:|---:|
| mean | 1393.9 ns | 1016.9 ns | **−27.0%** |
| p50 | 1211.6 ns | 903.8 ns | **−25.4%** |
| p95 | 1810.8 ns | 1352.2 ns | **−25.3%** |
| p99 | 3933.8 ns | 2455.2 ns | **−37.6%** |
| p99.9 | 21,499.4 ns | 15,682.8 ns | −27.1% |
| max (mean across trials) | 194,480 ns | 454,086.6 ns | not meaningful, see below |
| stdev of trial means | 261.5 ns | 63.5 ns | — |

**On `max`:** it went *up* in the variant's aggregate, but this is host-scheduler noise, not a real regression — one trial in the variant run happened to catch a large scheduling stall (consistent with the tail-latency finding from the validation phase, where max/p99.9 didn't correlate cleanly with anything causal on this 1-vCPU shared sandbox). Effect size at mean/p50/p95/p99 is 15–27x the trial-to-trial stdev, so those are reproducible; max at n=5 trials is not a number I'd trust for a go/no-go call, consistent with the "no p99.9/max claims from a single run" rule — five trials isn't enough to trust max specifically, only enough for percentiles up to roughly p99.

---

## Correctness results (variant, full scale)

| test | result |
|---|---|
| 400,000-step property test (`trials=20000, steps=20, seed=42`) | **0 failures** |
| 7,500-step differential test vs. C (`runtimes=500, steps=15, seed=7`) | **0 mismatches** |
| Existing manual test suite (16 tests) | **16/16 passed** |

All green — but see the next section for why "all green" doesn't settle this.

---

## Explicit type-tolerance test: does removing `int()` change behavior for real inputs?

Checked every `InputSample(` construction site in the repo (`Tests/`, `tests_correctness/`, `bench/`) — **all of them pass literal ints or `random.randint()` output**. No existing caller passes `numpy.int64`, `bool`, `float`, or `Decimal`. That's why the 400k-step property test and 7,500-step differential test show zero failures for the variant: those tests, and every other caller in this codebase, structurally only ever exercise the `int` path, so they can't see a divergence that only exists off that path.

I then constructed `InputSample` directly with each of those types to see what actually happens:

| input type | current (`int()` present) | variant (`int()` removed) |
|---|---|---|
| `numpy.int64(100)` | coerced to plain `int` | **stays `numpy.int64`** — type leaks into `Decision.value`/`.delta` |
| `True` (bool) | coerced to `int` → `1` | **stays `bool`** — `Decision.value == True`, not `1` (though `True == 1` in Python, `isinstance` checks downstream would differ) |
| `100.7` (float) | coerced to `int` → **truncated to `100`** | **stays `100.7`** — no truncation. `delta` becomes a float too (`abs(100.7 - 0) == 100.7`), not an int |
| `Decimal(100)` | coerced to `int` | **stays `Decimal('100')`** |

**The float case is the important one.** The current `int()` call isn't only a type guard — for float input it's a **truncation step**, matching the C reference's `int32_t` semantics (which also truncates on any implicit float→int32 conversion at the FFI boundary, though in practice the C side only ever receives ints from the differential-test harness). Removing `int()` doesn't just relax type strictness, it changes the *numeric value* that ends up in `Decision` for float input, and changes `delta`'s type from `int` to whatever the input type was.

---

## Interpretation

- The speedup is real and reproducible (25–38% depending on percentile, effect size far outside trial noise) — consistent with the isolated int-removal number from the original validation phase (−19.4%); slightly larger here likely because it's now measured on top of NamedTuple rather than the original dataclass, so there's less other per-call work diluting the relative effect.
- Correctness suites passing 100% is expected and not very informative here, because none of them exercise non-`int` input — this is a case where "tests pass" doesn't mean "behavior unchanged," it means "the specific inputs we test with don't happen to exercise the changed code path's edge cases."
- Whether this is safe to merge depends entirely on a question this repo's tests can't answer: **is passing a non-`int` (especially a `float`) into `InputSample.value`/`.threshold` a supported use case anywhere upstream of this package?** If yes, this variant silently changes runtime behavior (loses truncation) for those callers with no error and no test coverage catching it. If no — if `int` is genuinely the only type ever passed in practice — the change is safe and the current `int()` calls are dead-weight defensive coding.

## Recommendation

**Do not merge yet**, per your instruction and per this finding. This isn't a "tests failed" situation — it's a "tests can't tell us" situation, which is a different and arguably more important thing to flag before a merge decision, not less. I'd want an explicit answer from whoever owns the calling contract on the float-truncation question before proceeding. If the answer is "ints only, always," this is a clean 25–38% win with no real downside and I'd recommend merging it as a second isolated commit (same pattern as the NamedTuple change — one file, minimal diff, its own commit message). If floats or other numeric-like types are ever passed, the `int()` calls should stay, and this variant should be dropped.

No production code changed. Nothing committed. Raw data attached.
