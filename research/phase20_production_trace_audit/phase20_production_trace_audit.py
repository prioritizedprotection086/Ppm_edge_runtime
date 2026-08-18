#!/usr/bin/env python3
"""Phase 20 — Production-only audit of prioritizedprotection086/Ppm_edge_runtime main.

Uses ONLY real C/Python runtime. No FormalPolicy harness.
Does not modify production sources.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
if not (REPO / "Src" / "Ppm_edge.c").exists():
    REPO = Path(os.environ.get("PPM_REPO", "/tmp/Ppm_p20"))

sys.path.insert(0, str(REPO / "src"))
from ppm_edge import InputSample, PPMRuntime, Priority  # noqa: E402

INT32_MAX = 2**31 - 1
INT32_MIN = -(2**31)
SEED = 20
FAILURES: List[Dict[str, Any]] = []
MATRIX: Dict[str, Any] = {}
RESULTS: Dict[str, Any] = {
    "phase": 20,
    "repo": str(REPO),
    "commit": None,
    "label": "production-only audit of Ppm_edge_runtime main",
    "production_flags": {},
    "flag_evidence": {},
    "matrix": MATRIX,
    "failures": FAILURES,
    "python_c_comparison": [],
    "c_build": {},
    "sections": {
        "A_production_findings": [],
        "B_harness_only_phases_13_19": [],
        "C_unsupported_claims": [],
    },
}


def fail(test: str, **kwargs: Any) -> None:
    FAILURES.append({"test": test, **kwargs})


def py_seq(
    signals: List[int],
    threshold: int = 10,
    priorities: Optional[List[Priority]] = None,
    baseline: int = 0,
    reset_before_index: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rt = PPMRuntime()
    rt.state.baseline = baseline
    rt.state.last_value = baseline
    rt.threshold = max(0, int(threshold))
    rows = []
    for i, sig in enumerate(signals):
        if reset_before_index is not None and i == reset_before_index:
            rt.reset()
        pr = priorities[i] if priorities else Priority.NORMAL
        d = rt.process(InputSample(value=int(sig), threshold=threshold, priority=pr))
        assert d is not None
        rows.append(
            {
                "value": d.value,
                "delta": int(d.delta),
                "protected": bool(d.protected),
                "confidence": int(d.confidence),
                "priority": int(d.priority),
            }
        )
    return rows


def inventory_flags() -> None:
    c = (REPO / "Src" / "Ppm_edge.c").read_text()
    h = (REPO / "Src" / "Ppm_edge.h").read_text()
    py = (REPO / "src" / "ppm_edge" / "runtime.py").read_text()
    blob = c + h + py

    def absent(*needles: str) -> bool:
        return not any(n in blob for n in needles)

    evidence = {
        "PRODUCTION_HAS_GLOBAL_PATH_BUDGET": {
            "value": not absent() and False,  # placeholder
            "evidence": "",
            "files": ["Src/Ppm_edge.c:ppm_process", "src/ppm_edge/runtime.py:PPMRuntime.process"],
        }
    }
    # explicit false with evidence
    evidence = {
        "PRODUCTION_HAS_GLOBAL_PATH_BUDGET": {
            "value": False,
            "evidence": (
                "No path_sum/B_global/total_path symbols in Src/Ppm_edge.c, Src/Ppm_edge.h, "
                "or src/ppm_edge/runtime.py. ppm_process always updates last_value and fills "
                "ppm_output_t; never rejects on cumulative path cost."
            ),
            "files": ["Src/Ppm_edge.c:ppm_process", "src/ppm_edge/runtime.py:PPMRuntime.process"],
        },
        "PRODUCTION_HAS_ORIGIN_BUDGET": {
            "value": False,
            "evidence": (
                "ppm_runtime_t (Src/Ppm_edge.h) has baseline, last_value, threshold, flags, "
                "priority only — no origin or origin_budget. RuntimeState in runtime.py same."
            ),
            "files": ["Src/Ppm_edge.h:ppm_runtime_t", "src/ppm_edge/runtime.py:RuntimeState"],
        },
        "PRODUCTION_HAS_CHECKPOINTS": {
            "value": False,
            "evidence": (
                "Public C API is only ppm_init, ppm_reset, ppm_process, ppm_version "
                "(Src/Ppm_edge.h). No checkpoint/serialize/MAC."
            ),
            "files": ["Src/Ppm_edge.h"],
        },
        "PRODUCTION_HAS_RECOVERY": {
            "value": False,
            "evidence": (
                "ppm_reset (Src/Ppm_edge.c) sets last_value=baseline and clears flags. "
                "PPMRuntime.reset mirrors that. Not checkpoint high-water recovery."
            ),
            "files": ["Src/Ppm_edge.c:ppm_reset", "src/ppm_edge/runtime.py:PPMRuntime.reset"],
        },
        "PRODUCTION_HAS_REAUTH": {
            "value": False,
            "evidence": (
                "No session_id, epoch, reauth, or token fields in C header or Python runtime."
            ),
            "files": ["Src/Ppm_edge.h", "src/ppm_edge/runtime.py"],
        },
        "PRODUCTION_HAS_ATOMIC_BUDGET_ACCOUNTING": {
            "value": False,
            "evidence": (
                "No version/CAS/path budget. ppm_process performs direct field writes only."
            ),
            "files": ["Src/Ppm_edge.c:ppm_process"],
        },
    }
    # verify needles not present
    checks = {
        "PRODUCTION_HAS_GLOBAL_PATH_BUDGET": ["path_sum", "B_global", "b_global", "total_path"],
        "PRODUCTION_HAS_ORIGIN_BUDGET": ["origin_budget"],
        "PRODUCTION_HAS_CHECKPOINTS": ["checkpoint"],
        "PRODUCTION_HAS_REAUTH": ["reauth", "session_id"],
    }
    for k, needles in checks.items():
        if any(n in blob for n in needles):
            evidence[k]["value"] = True
            evidence[k]["evidence"] += " UNEXPECTED_NEEDLE_FOUND"

    RESULTS["flag_evidence"] = evidence
    RESULTS["production_flags"] = {k: v["value"] for k, v in evidence.items()}
    RESULTS["sections"]["A_production_findings"].append(
        "Production implements threshold + CRITICAL priority protection; always accepts samples."
    )
    RESULTS["sections"]["B_harness_only_phases_13_19"].append(
        "B_global, origin budget, checkpoints, reauth, CAS interleavings exist only under research/phase14+ harness."
    )
    RESULTS["sections"]["C_unsupported_claims"].append(
        "Claims that production enforces global path budget, origin budget, checkpoints, or reauth are unsupported on main."
    )


def run_named(name: str, fn) -> bool:
    print(f"Running {name}...", flush=True)
    try:
        ok = fn()
    except Exception as e:
        ok = False
        fail(name, error=str(e), severity="high")
        MATRIX[name] = {"pass": False, "error": str(e)}
        print(f"  ERROR: {e}")
        return False
    MATRIX[name] = {**MATRIX.get(name, {}), "pass": ok}
    print(f"  {'PASS' if ok else 'FAIL'}")
    return ok


def test_threshold() -> bool:
    name = "THRESHOLD_BOUNDARIES"
    r9, r10, r11 = py_seq([0, 9], 10), py_seq([0, 10], 10), py_seq([0, 11], 10)
    ok = (
        r9[1]["delta"] == 9
        and r9[1]["protected"] is False
        and r10[1]["delta"] == 10
        and r10[1]["protected"] is True
        and r11[1]["delta"] == 11
        and r11[1]["protected"] is True
    )
    if not ok:
        fail(name, file="src/ppm_edge/runtime.py", function="process", actual={"9": r9[1], "10": r10[1], "11": r11[1]}, severity="high")
    MATRIX[name] = {"pass": ok, "r9": r9[1], "r10": r10[1], "r11": r11[1]}
    return ok


def test_zero() -> bool:
    name = "ZERO_DELTA"
    r = py_seq([42, 42], 10)
    ok = r[1]["delta"] == 0 and r[1]["protected"] is False and r[1]["confidence"] == 100
    if not ok:
        fail(name, actual=r[1], severity="medium")
    MATRIX[name] = {"pass": ok, "row": r[1]}
    return ok


def test_pos_neg() -> bool:
    name = "POS_NEG_DELTAS"
    r = py_seq([100, 90, 110], 15)
    ok = r[1]["delta"] == 10 and not r[1]["protected"] and r[2]["delta"] == 20 and r[2]["protected"]
    if not ok:
        fail(name, actual=r, severity="high")
    MATRIX[name] = {"pass": ok, "trace": r}
    return ok


def test_int32() -> bool:
    name = "INT32_EXTREMES"
    ok = True
    detail = {}
    r = py_seq([0, INT32_MAX], 1)
    detail["max"] = r[1]
    if r[1]["delta"] != INT32_MAX or not r[1]["protected"]:
        ok = False
        fail(name, input=[0, INT32_MAX], actual=r[1], severity="high")
    r = py_seq([0, INT32_MIN], 1)
    detail["min"] = r[1]
    if r[1]["delta"] != 2**31 or not r[1]["protected"]:
        ok = False
        fail(name, input=[0, INT32_MIN], actual=r[1], severity="high")
    r = py_seq([INT32_MIN, INT32_MAX], 1)
    detail["span"] = r[1]
    if r[1]["delta"] != (INT32_MAX - INT32_MIN):
        ok = False
        fail(name, input=[INT32_MIN, INT32_MAX], actual=r[1], expected=INT32_MAX - INT32_MIN, severity="medium")
    MATRIX[name] = {"pass": ok, "detail": detail}
    return ok


def test_repeated() -> bool:
    name = "REPEATED"
    r = py_seq([7] * 50, 1)
    ok = all(x["delta"] == 0 and not x["protected"] for x in r[1:])
    MATRIX[name] = {"pass": ok}
    if not ok:
        fail(name, severity="medium")
    return ok


def test_reset() -> bool:
    name = "RESET"
    r = py_seq([50, 5], 10, reset_before_index=1)
    ok = r[1]["delta"] == 5 and not r[1]["protected"]
    if not ok:
        fail(name, actual=r, severity="high")
    MATRIX[name] = {"pass": ok, "after_reset": r[1]}
    return ok


def test_critical() -> bool:
    name = "CRITICAL_PRIORITY"
    r = py_seq([0, 1], 100, [Priority.NORMAL, Priority.CRITICAL])
    ok = r[1]["delta"] == 1 and r[1]["protected"] is True
    if not ok:
        fail(name, actual=r[1], severity="high")
    MATRIX[name] = {"pass": ok, "row": r[1]}
    return ok


def test_neg_th() -> bool:
    name = "NEGATIVE_THRESHOLD"
    r = py_seq([0, 1], -5)
    ok = r[1]["delta"] == 1 and r[1]["protected"] is True
    if not ok:
        fail(name, actual=r[1], severity="medium")
    MATRIX[name] = {"pass": ok, "row": r[1]}
    return ok


def test_random() -> bool:
    name = "LONG_RANDOMIZED"
    rng = random.Random(SEED)
    vals = [rng.randint(-10000, 10000) for _ in range(10000)]
    th = 25
    r = py_seq(vals, th)
    ok = len(r) == 10000
    for i in range(1, len(r)):
        if r[i]["protected"] != (r[i]["delta"] >= th):
            ok = False
            fail(name, operation_index=i, actual=r[i], severity="high")
            break
    MATRIX[name] = {"pass": ok, "n": len(r)}
    return ok


def build_driver(sanitize: bool) -> Dict[str, Any]:
    build_dir = REPO / "build_phase20"
    build_dir.mkdir(exist_ok=True)
    driver = Path(__file__).resolve().parent / "c_trace_driver.c"
    out_bin = build_dir / ("c_trace_asan" if sanitize else "c_trace")
    cmd = ["gcc", "-std=c11", "-Wall", "-Wextra", "-g", "-O1", f"-I{REPO / 'Src'}", str(REPO / "Src" / "Ppm_edge.c"), str(driver), "-o", str(out_bin)]
    if sanitize:
        cmd[4:4] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    info: Dict[str, Any] = {"cmd": " ".join(cmd), "sanitize": sanitize, "built": False, "ran": False}
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    info["build_returncode"] = p.returncode
    info["build_stderr"] = (p.stderr or "")[-1200:]
    if p.returncode != 0:
        return info
    info["built"] = True
    env = {**os.environ}
    if sanitize:
        env["ASAN_OPTIONS"] = "detect_leaks=0"
    r = subprocess.run([str(out_bin)], capture_output=True, text=True, timeout=30, env=env)
    info["ran"] = r.returncode == 0
    info["returncode"] = r.returncode
    info["stdout"] = r.stdout
    info["stderr"] = (r.stderr or "")[-1200:]
    return info


def parse_c(stdout: str) -> Dict[str, List[Dict[str, Any]]]:
    suites: Dict[str, List[Dict[str, Any]]] = {}
    cur = None
    for line in stdout.splitlines():
        if line.startswith("SUITE "):
            cur = line.split(" ", 1)[1].strip()
            suites[cur] = []
        elif line.startswith("ROW ") and cur:
            p = line.split()
            suites[cur].append(
                {
                    "value": int(p[1]),
                    "delta": int(p[2]),
                    "protected": p[3] != "0",
                    "confidence": int(p[4]),
                    "priority": int(p[5]),
                }
            )
    return suites


def test_c_build() -> bool:
    name = "C_CMAKE_AND_SANITIZERS"
    demo = REPO / "build" / "ppm_demo"
    demo_ok = False
    if demo.exists():
        d = subprocess.run([str(demo)], capture_output=True, text=True, timeout=10)
        demo_ok = d.returncode == 0
        RESULTS["c_build"]["demo_output"] = d.stdout
    asan = build_driver(True)
    plain = build_driver(False)
    RESULTS["c_build"]["asan"] = {k: asan.get(k) for k in ("built", "ran", "returncode", "build_returncode", "stderr")}
    RESULTS["c_build"]["plain"] = {k: plain.get(k) for k in ("built", "ran", "returncode", "build_returncode", "stderr")}
    RESULTS["_c_stdout"] = asan.get("stdout") or plain.get("stdout") or ""
    ok = demo_ok and asan.get("built") and asan.get("ran") and plain.get("built") and plain.get("ran")
    if not ok:
        fail(name, command=asan.get("cmd"), actual=RESULTS["c_build"], severity="high")
    MATRIX[name] = {"pass": ok, "demo_ok": demo_ok, "asan": asan.get("ran"), "plain": plain.get("ran")}
    return ok


def test_py_c() -> bool:
    name = "PYTHON_C_IDENTICAL_TRACES"
    stdout = RESULTS.get("_c_stdout") or ""
    suites = parse_c(stdout)
    if not suites:
        fail(name, expected="C suites", actual="empty", severity="high")
        MATRIX[name] = {"pass": False}
        return False
    ok = True
    comparisons = []

    def cmp_suite(sname, py_rows, c_rows, check_delta=True):
        nonlocal ok
        if len(py_rows) != len(c_rows):
            ok = False
            fail(sname, expected=len(py_rows), actual=len(c_rows), severity="high")
            return
        for i, (p, c) in enumerate(zip(py_rows, c_rows)):
            match = p["value"] == c["value"] and p["protected"] == c["protected"]
            if check_delta:
                match = match and p["delta"] == c["delta"]
            comparisons.append({"suite": sname, "i": i, "match": match, "py": p, "c": c})
            if not match:
                ok = False
                fail(name, suite=sname, i=i, expected=p, actual=c, file="Src/Ppm_edge.c vs runtime.py", severity="high")

    cmp_suite("threshold", py_seq([0, 9], 10) + py_seq([0, 10], 10) + py_seq([0, 11], 10), suites.get("threshold", []))
    cmp_suite("zero_delta", py_seq([42, 42], 10), suites.get("zero_delta", []))
    cmp_suite("pos_neg", py_seq([100, 90, 110], 15), suites.get("pos_neg", []))
    cmp_suite("critical", py_seq([0, 1], 100, [Priority.NORMAL, Priority.CRITICAL]), suites.get("critical", []))
    cmp_suite("neg_threshold", py_seq([0, 1], -5), suites.get("neg_threshold", []))
    cmp_suite("reset", py_seq([50, 5], 10, reset_before_index=1), suites.get("reset", []))
    cmp_suite("repeated", py_seq([7] * 20, 1), suites.get("repeated", []))
    # int32: protection+value must match; delta may differ (Python int vs C uint32)
    py_i = py_seq([0, INT32_MAX], 1) + py_seq([0, INT32_MIN], 1) + py_seq([INT32_MIN, INT32_MAX], 1)
    c_i = suites.get("int32", [])
    if len(py_i) == len(c_i):
        for i, (p, c) in enumerate(zip(py_i, c_i)):
            match = p["value"] == c["value"] and p["protected"] == c["protected"]
            comparisons.append({"suite": "int32", "i": i, "match_value_prot": match, "py_delta": p["delta"], "c_delta": c["delta"]})
            if not match:
                ok = False
                fail(name, suite="int32", i=i, expected=p, actual=c, severity="high")
    else:
        ok = False
        fail(name, suite="int32", expected=len(py_i), actual=len(c_i), severity="high")
    RESULTS["python_c_comparison"] = comparisons
    MATRIX[name] = {"pass": ok, "suites": list(suites.keys())}
    return ok


def main() -> int:
    print("=== PHASE 20 Production Trace Audit (main only) ===\n")
    print(f"REPO={REPO}")
    try:
        RESULTS["commit"] = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        RESULTS["commit"] = None
    print(f"commit={RESULTS['commit']}\n")
    inventory_flags()
    for k, v in RESULTS["production_flags"].items():
        print(f"  {k} = {v}")
    all_pass = True
    for label, fn in [
        ("THRESHOLD_BOUNDARIES", test_threshold),
        ("ZERO_DELTA", test_zero),
        ("POS_NEG_DELTAS", test_pos_neg),
        ("INT32_EXTREMES", test_int32),
        ("REPEATED", test_repeated),
        ("RESET", test_reset),
        ("CRITICAL_PRIORITY", test_critical),
        ("NEGATIVE_THRESHOLD", test_neg_th),
        ("LONG_RANDOMIZED", test_random),
        ("C_CMAKE_AND_SANITIZERS", test_c_build),
        ("PYTHON_C_IDENTICAL_TRACES", test_py_c),
    ]:
        if not run_named(label, fn):
            all_pass = False
    RESULTS["all_pass"] = all_pass
    RESULTS["failure_count"] = len(FAILURES)
    print("\n=== PASS/FAIL MATRIX ===")
    for k, v in MATRIX.items():
        print(f"  {'PASS' if v.get('pass') else 'FAIL'}: {k}")
    print(f"\nALL_PASS={all_pass} failures={len(FAILURES)}")
    print("\n=== FLAGS ===")
    for k, v in RESULTS["production_flags"].items():
        print(f"  {k} = {v}")
    RESULTS.pop("_c_stdout", None)
    out = Path(__file__).resolve().parent / "PHASE_20_RESULTS.json"
    with open(out, "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    print(f"\nWrote {out}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
