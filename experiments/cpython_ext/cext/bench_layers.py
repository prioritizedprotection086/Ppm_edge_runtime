"""Benchmarks the CPython C-extension layer (ppm_edge_ext) and the pure
Python PPM runtime layer (ppm_edge.runtime.PPMRuntime), using the exact
same input generator, seeds, and scale as the isolated-C benchmark
(benchmark/c_bench/), so all three layers are directly comparable:

  - 5 independent trials, seeds [401, 402, 403, 404, 405]
  - 5,000 warmup ops (untimed) + 1,000,000 measured ops per trial
  - each measured call individually timed via time.perf_counter_ns()
  - percentiles (p50/p95/p99/p99.9/max/mean) via numpy.percentile,
    identical methodology to benchmark/c_bench/analyze.py and
    benchmark/harness.py

Both layers are run in this same process, back to back, on this same
machine, at the same time as each other and as the isolated-C run they're
being compared against, so the comparison isn't confounded by machine or
time-of-run differences.

Does not modify src/ppm_edge, Src/, or Tests/.
"""
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path("/home/claude/work/scratch/ppm_edge_repo")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "benchmark"))
sys.path.insert(0, str(REPO / "benchmark" / "cext"))

from ppm_edge.runtime import PPMRuntime, InputSample, Priority  # noqa: E402
from inputs import generate_trial_inputs  # noqa: E402
import ppm_edge_ext  # noqa: E402

N_WARMUP = 5_000
N_MEASURED = 1_000_000
SEEDS = [401, 402, 403, 404, 405]

OUT_DIR = REPO / "benchmark" / "cext" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def percentiles(arr):
    return {
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "p99.9": float(np.percentile(arr, 99.9)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def bench_cext(trial_inputs):
    initial = trial_inputs["initial_value"]
    values, thresholds, priorities = (
        trial_inputs["values"], trial_inputs["thresholds"], trial_inputs["priorities"]
    )
    n_w, n_m = trial_inputs["n_warmup"], trial_inputs["n_measured"]

    runtime = ppm_edge_ext.PPMRuntimeExt(int(initial))
    for i in range(n_w):
        runtime.process(int(values[i]), int(thresholds[i]), int(priorities[i]))

    gc.collect()

    lat = np.empty(n_m, dtype=np.int64)
    t_wall0 = time.perf_counter()
    for j in range(n_m):
        i = n_w + j
        t0 = time.perf_counter_ns()
        runtime.process(int(values[i]), int(thresholds[i]), int(priorities[i]))
        t1 = time.perf_counter_ns()
        lat[j] = t1 - t0
    wall = time.perf_counter() - t_wall0

    return {
        "latency_ns": percentiles(lat),
        "wall_s": wall,
        "throughput_ops_per_sec": n_m / wall,
    }


def bench_python_reference(trial_inputs):
    initial = trial_inputs["initial_value"]
    values, thresholds, priorities = (
        trial_inputs["values"], trial_inputs["thresholds"], trial_inputs["priorities"]
    )
    n_w, n_m = trial_inputs["n_warmup"], trial_inputs["n_measured"]

    priority_lut = [Priority.LOW, Priority.NORMAL, Priority.HIGH, Priority.CRITICAL]
    priority_objs = [priority_lut[int(p)] for p in priorities]

    runtime = PPMRuntime(initial_value=int(initial))
    for i in range(n_w):
        runtime.process(InputSample(value=int(values[i]), threshold=int(thresholds[i]), priority=priority_objs[i]))

    gc.collect()

    lat = np.empty(n_m, dtype=np.int64)
    t_wall0 = time.perf_counter()
    for j in range(n_m):
        i = n_w + j
        t0 = time.perf_counter_ns()
        runtime.process(InputSample(value=int(values[i]), threshold=int(thresholds[i]), priority=priority_objs[i]))
        t1 = time.perf_counter_ns()
        lat[j] = t1 - t0
    wall = time.perf_counter() - t_wall0

    return {
        "latency_ns": percentiles(lat),
        "wall_s": wall,
        "throughput_ops_per_sec": n_m / wall,
    }


LAYERS = {
    "cpython_c_extension": bench_cext,
    "pure_python_ppm_runtime": bench_python_reference,
}


def main():
    all_results = {name: [] for name in LAYERS}

    for seed in SEEDS:
        trial_inputs = generate_trial_inputs(seed, N_WARMUP, N_MEASURED)
        print(f"=== Trial seed={seed} ===")
        for name, fn in LAYERS.items():
            result = fn(trial_inputs)
            result["seed"] = seed
            all_results[name].append(result)
            lp = result["latency_ns"]
            print(f"  {name:26s} p50={lp['p50']:>8.1f}ns  p99={lp['p99']:>9.1f}ns  "
                  f"p99.9={lp['p99.9']:>9.1f}ns  max={lp['max']:>10.1f}ns  "
                  f"throughput={result['throughput_ops_per_sec']:>12.0f} ops/s")
        print()

    metrics = ["p50", "p95", "p99", "p99.9", "max", "mean"]
    aggregate = {}
    for name in LAYERS:
        agg = {}
        for m in metrics:
            vals = np.array([t["latency_ns"][m] for t in all_results[name]])
            agg[m] = {"mean": float(vals.mean()), "stdev": float(vals.std()),
                       "min": float(vals.min()), "max": float(vals.max())}
        thr = np.array([t["throughput_ops_per_sec"] for t in all_results[name]])
        wall = np.array([t["wall_s"] for t in all_results[name]])
        agg["throughput_ops_per_sec"] = {"mean": float(thr.mean()), "stdev": float(thr.std()),
                                          "min": float(thr.min()), "max": float(thr.max())}
        agg["wall_seconds"] = {"mean": float(wall.mean()), "stdev": float(wall.std()),
                                "min": float(wall.min()), "max": float(wall.max())}
        aggregate[name] = agg

        print(f"\n=== Aggregate: {name} (across {len(SEEDS)} trials) ===")
        for m in metrics:
            a = agg[m]
            print(f"  {m:6s}: mean={a['mean']:>12.1f}ns  stdev={a['stdev']:>10.1f}ns  "
                  f"min={a['min']:>12.1f}  max={a['max']:>12.1f}")
        print(f"  throughput: mean={agg['throughput_ops_per_sec']['mean']:>14.0f} ops/s  "
              f"stdev={agg['throughput_ops_per_sec']['stdev']:>10.0f}")

    out = {
        "n_warmup": N_WARMUP,
        "n_measured": N_MEASURED,
        "seeds": SEEDS,
        "per_trial": all_results,
        "aggregate": aggregate,
    }
    out_path = OUT_DIR / "cext_and_python_layers_summary.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
