"""3-way differential test: Python reference PPMRuntime vs. the existing
ctypes C-kernel baseline vs. the new CPython C-extension (ppm_edge_ext),
over the same deterministic 7,500-step stream used by
benchmark/differential_test.py (seed=42).

Confirms the new extension is behaviorally identical to both the Python
reference and the already-verified ctypes C kernel before any timing
numbers from it are trusted. Does not modify Src/, src/, or Tests/.
"""
import random
import sys
from pathlib import Path

REPO = Path("/home/claude/work/scratch/ppm_edge_repo")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "benchmark"))
sys.path.insert(0, str(REPO / "benchmark" / "cext"))

from ppm_edge.runtime import PPMRuntime, InputSample, Priority  # noqa: E402
from baselines.c_kernel import CKernelBaseline  # noqa: E402
import ppm_edge_ext  # noqa: E402

STEPS = 7500
SEED = 42


def run():
    rng = random.Random(SEED)
    initial_value = rng.randint(-10_000, 10_000)

    py_runtime = PPMRuntime(initial_value=initial_value)
    c_runtime = CKernelBaseline(initial_value=initial_value)
    ext_runtime = ppm_edge_ext.PPMRuntimeExt(initial_value)

    priorities = list(Priority)
    mismatches = []

    for i in range(STEPS):
        value = rng.randint(-1_000_000, 1_000_000)
        threshold = rng.randint(0, 50_000)
        priority = priorities[i % 4]

        py_dec = py_runtime.process(
            InputSample(value=value, threshold=threshold, priority=priority)
        )
        c_out = c_runtime.process(value, threshold, int(priority))
        ext_out = ext_runtime.process(value, threshold, int(priority))

        py_tuple = (py_dec.value, py_dec.delta, py_dec.protected, py_dec.confidence, int(py_dec.priority))

        if py_tuple != c_out:
            mismatches.append(("py_vs_c", i, py_tuple, c_out))
        if py_tuple != ext_out:
            mismatches.append(("py_vs_ext", i, py_tuple, ext_out))
        if c_out != ext_out:
            mismatches.append(("c_vs_ext", i, c_out, ext_out))

    print(f"3-way differential test: {STEPS} steps, seed={SEED}")
    print(f"{len(mismatches)} mismatches")
    if mismatches:
        for m in mismatches[:10]:
            print(m)
        sys.exit(1)


if __name__ == "__main__":
    run()
