# Full Chat Session Record — PPM-Edge Research

**Exported:** 2026-08-17T00:37:06.709762Z  
**Workspace:** /home/workdir/artifacts  

This file aggregates the data, findings, and artifacts from the Grok session on the PPM-Edge repository (prioritizedprotection086/Ppm_edge_runtime).

---

## 1. Repository audit (start of session)

### GitHub repo
- Owner/repo: `prioritizedprotection086/Ppm_edge_runtime`
- Default branch: `main`
- Tip at audit: `38d27b888b6719e2b37bbe2df7391d600de91243` — "Add files via upload"
- History: 23 commits, linear, **zero tags** on remote
- Other remote branches seen on website: `main`, `import/uploaded-files`, `benchmark-layer`

### Missing from Git (referenced only in V1 docs)
| Identifier | Status |
|------------|--------|
| Tag `v1-demo-freeze` | Missing |
| Commit `37145182805357a8cc372b3539a3ab7c05fa1f1e` | Missing |
| Commit `235ab5f636b3868fa7bb92987ec74647969ae5ed` | Missing |
| V2 research artifacts | Missing |
| V2.1 contract-hardening | Missing |
| Four contract strategies | Missing |
| Test-vector generator (original) | Missing |
| Corrected performance harness (original) | Missing |

### Present
- Production C/Python sources on `main`
- Zip `ppm_edge_runtime_demo_v1_ALL.zip` containing V1 demo + `DEMO_EVIDENCE.md`, `DEMO_SCRIPT.md`, `MASTER_SESSION_RECORD.md`
- CI file (later replaced in local research branch)

### Labeling rule used
- Anything regenerated in this sandbox = **RECONSTRUCTED**
- Original Claude V2/V2.1 work was **not recovered** from Git

---

## 2. Local git state (end of session)

```
fa3b476 Configure GitHub Actions: production CI + research workflow
992e9c5 Add isolated adversarial policy-layer research artifacts (RECONSTRUCTED)
38d27b8 Add files via upload
212839e Fix include case sensitivity for Ppm_edge.h
c3937dd Rename header file from ppm_edge.h to Ppm_edge.h
---
  main                              38d27b8 Add files via upload
* research/adversarial-policy-layer fa3b476 Configure GitHub Actions: production CI + research workflow
---
fa3b4766be8736fcef9908f3b02e693b6369ef1b
38d27b888b6719e2b37bbe2df7391d600de91243
## research/adversarial-policy-layer

```

### Local commits on `research/adversarial-policy-layer`
1. `992e9c534fc649bc53f917158b9e1dd0ff90544e` — research artifacts under `research/adversarial_policy/`
2. `fa3b4766be8736fcef9908f3b02e693b6369ef1b` — GitHub Actions ci.yml + research.yml

### Remote push
**Failed repeatedly:** GitHub App `403 Resource not accessible by integration`; HTTPS git has no credentials. Branch **not** on remote unless user pushed manually.

---

## 3. Experiments executed (verified)

| Experiment | Result |
|------------|--------|
| V1 `run_tests.py` | **30/30 passed** |
| Demo replay / boundary / live | PASS / MATCH / 0 mismatches |
| Pure-Python stress (50k–1M) | Determinism PASS; ~157k–457k ops/s |
| Multi-seed differential | ALL PASS |
| AI-adversarial recommendation battery | Documented PASS/PROTECT rates |
| Phase 1 bypass surface | Full map; hug = 0% PROTECT |
| Phase 2 adversarial max-harm zero-PROTECT | 90/90 zero-PROTECT; max path 2.45M |
| Phase 3 policy ablation | authority_delta + cum_disp_limit minimal set |
| Phase 4 red-team bare vs policy | slow_drift blocked; legit walk 0 false blocks |
| C standalone adversarial harness | ALL PASS |
| Three-way Python / C-ext / oracle | ALL PASS |
| Threshold-hugging grid (6600 cells) | 6504 full bypass; 96 full protect; rule: k≥1 → bypass |

### Provenance hashes (sha256[:16])
| Path | Hash |
|------|------|
| src/ppm_edge/runtime.py | adb93d09df2c11a1 |
| Src/Ppm_edge.c | ba10cee33d6efc1e |
| Src/Ppm_edge.h | 5e78e7ecd5ec073e |
| src/ppm_edge/__init__.py | 0974fdaadaf44bd2 |

---

## 4. Core scientific conclusions

### Contract
`protected = (delta >= threshold) OR priority == CRITICAL`  
Only persistent decision state: `last_value`. Memoryless otherwise.

### Bypass surface
Any NORMAL-priority sequence with `|Δ| ≤ threshold−1` has **0% PROTECT**, unbounded path length / net displacement / chatter.

### Minimal external policy (not in production kernel)
`authority_delta` + `cum_disp_limit` closes demonstrated slow_drift and large hugs with low false positives on small legitimate walks. Residual in-band attacks remain.

### Scope limit
PPM-Edge is a numeric interlock, not a semantic/intent layer.

---

## 5. Research report (full text)

# Research Report: PPM-Edge Bypass Surface & Minimal Policy Layer

**Date:** 2026-08-16  
**Scope:** Isolated experimental layer only. Production PPM-Edge kernel untouched.  
**Provenance (sha256[:16]):**
- `src/ppm_edge/runtime.py` = adb93d09df2c11a1
- `Src/Ppm_edge.c` = ba10cee33d6efc1e
- sandbox extension so = 659886f4b7e9ddbe

**Evidence discipline:** key experiments run twice independently; V1 gates re-run (30/30); raw JSON under experiments/results/.

---

## 1. How much harmful behavior can currently hide below the threshold?

Under the existing contract (`protected = delta >= threshold OR CRITICAL`):

| Pattern | PROTECT rate | Example scale |
|---------|--------------|---------------|
| Δ = threshold − 1 (hug) | **0%** | 200k steps, path length 4.8M, still 0 protects |
| Δ = threshold − k (k≥1) | **0%** | all tested thresholds 5–100 |
| Unidirectional slow drift at Δ=th−1 | **0%** | 100k steps → net displacement 100k×(th−1) |
| Alternating sub-threshold chatter | **0%** | 20k–50k steps, tens of thousands of reversals |
| Randomized avoid-PROTECT policy | **50/50 seeds full bypass** | path up to ~400k in 10k steps |

**Maximum demonstrated unprotected movement (50k steps, th=50):**
- Path length: **2,450,000**
- Net displacement (slow drift): **2,450,000**
- Reversals (hug/chatter): **49,999**

Initial state does not matter. Sequence length does not accumulate any hidden debt — the rule is memoryless except for `last_value`.

**Verified conclusion:** An adversarial AI that never sets CRITICAL and keeps |Δ| ≤ threshold−1 can produce unbounded cumulative displacement and arbitrary chatter with a 0% PROTECT rate.

---

## 2. Smallest policy layer that closes the demonstrated holes

Mechanisms tested one-at-a-time (external to the kernel):

| Mechanism | Closes slow_drift? | Closes hug/chatter? | False blocks on legitimate small walk? |
|-----------|--------------------|---------------------|----------------------------------------|
| authority_delta (hard \|Δ\| cap) | Yes | Partially (blocks steps > auth) | No (when auth ≥ typical legit step) |
| cum_disp_limit (from origin) | Yes | No (oscillation returns to origin) | No (if limit >> normal range) |
| rate limit (sum \|Δ\| in window) | Yes | Partial | Low if tuned |
| chatter limit (reversals in window) | No | Partial | **High** (false positives on normal walks) |

**Minimal effective set demonstrated:**  
`authority_delta` + `cum_disp_limit`

- slow_drift → 100% blocked (authority or cum_disp)  
- hug/chatter → steps larger than authority blocked; residual oscillation still possible inside the authority band  
- legitimate small walk (Δ≤3) → 0 false blocks with authority=20, cum=500  

Adding chatter limit without careful tuning harms legitimate traffic. Rate limit is useful but not required for the first cut.

---

## 3. New failure modes introduced by the policy layer

1. **Origin dependence (cum_disp):** if the legitimate operating point must move far from the original baseline (e.g., long-running setpoint change), cum_disp will eventually block honest motion unless origin is updated by a higher authority.
2. **Authority floor:** setting authority too tight rejects legitimate fast maneuvers; too loose re-opens slow_drift inside the band.
3. **No semantic understanding:** the layer still cannot see “contradiction,” “wrong goal,” or “manipulative intent” — only numeric envelopes.
4. **Residual in-band attack:** an adversary that stays inside both authority_delta and cum_disp_limit can still chatter or drift slowly within that box.

---

## 4. What remains fundamentally outside PPM-Edge’s scope

- Intent, contradiction, authority *labels*, world models, task constraints  
- Any property that cannot be reduced to (value, threshold, priority) or simple functions of recent numeric history  
- Deciding whether a sub-threshold move is “good” or “bad” for the robot’s mission  

PPM-Edge is a **fast, deterministic numeric gate**, not a planner or a value-alignment system.

---

## 5. Implications for AI planner → physical robot

The architecture is useful as a **last numeric safety interlock**:

- It reliably stops gross, blunt, or incompetent large moves when threshold is set to the real physical/authority envelope.  
- It does **not** stop a capable adversarial or simply optimizing AI that respects the numeric envelope while still being wrong.  

Therefore:

1. Keep PPM-Edge thin, fast, and verified (current state is good).  
2. Put a small, explicit policy layer *above* it for cumulative displacement and hard authority caps.  
3. Treat anything requiring semantics (contradiction, goal appropriateness, long-horizon harm) as a separate, slower layer — not as an extension of this kernel.  
4. Never rely on the boundary alone against an AI that can read the rule.

**Bottom line:** PPM-Edge is a trustworthy calculator of a simple rule. The demonstrated bypasses are not bugs in that rule; they are the rule working exactly as specified. Closing the robotics-relevant holes requires policy above the kernel, not a smarter kernel.

---

## Evidence index
- experiments/results/phase1_bypass_surface.json  
- experiments/results/phase2_adversarial.json  
- experiments/results/phase3_policy_ablation.json  
- experiments/results/phase4_redteam.json  
- V1 gates after all experiments: 30/30 passed  
- Independent re-runs: long hug, best-path attack, red-team modes — matched  


---

## 6. Phase JSON summaries

```json
{
  "phase1_bypass_surface.json": {
    "keys": [
      "fixed_subthreshold",
      "cumulative_small",
      "chatter",
      "initial_states",
      "random_avoid",
      "long_hug"
    ],
    "long_hug": {
      "th": 25,
      "delta": 24,
      "n": 200000,
      "prot": 0,
      "path": 4800000,
      "net": 0
    },
    "random_avoid": {
      "full_bypass_rate": 1.0,
      "best": {
        "seed": 44,
        "th": 80,
        "path": 402492,
        "net": 2596,
        "n": 10000
      }
    }
  },
  "phase2_adversarial.json": {
    "best_path": {
      "prot": 0,
      "path": 2450000,
      "net": 0,
      "reversals": 49999,
      "max_excursion": 49,
      "n": 50000,
      "final": 0,
      "th": 50,
      "mode": "hug",
      "seed": 0
    },
    "best_net": {
      "prot": 0,
      "path": 2450000,
      "net": 2450000,
      "reversals": 0,
      "max_excursion": 2450000,
      "n": 50000,
      "final": 2450000,
      "th": 50,
      "mode": "slow_drift",
      "seed": 0
    },
    "best_excursion": {
      "prot": 0,
      "path": 2450000,
      "net": 2450000,
      "reversals": 0,
      "max_excursion": 2450000,
      "n": 50000,
      "final": 2450000,
      "th": 50,
      "mode": "slow_drift",
      "seed": 0
    },
    "best_reversals": {
      "prot": 0,
      "path": 450000,
      "net": 0,
      "reversals": 49999,
      "max_excursion": 9,
      "n": 50000,
      "final": 0,
      "th": 10,
      "mode": "hug",
      "seed": 0
    },
    "n_rows": 90
  },
  "phase3_policy_ablation.json": [
    {
      "config": "authority only (\u0394\u226420)",
      "mode": "slow_drift",
      "pass_through": 0,
      "policy_block": 20000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 20000
      },
      "pol_passed": 0,
      "pol_blocked": 20000
    },
    {
      "config": "authority only (\u0394\u226420)",
      "mode": "hug",
      "pass_through": 10000,
      "policy_block": 10000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 10000
      },
      "pol_passed": 10000,
      "pol_blocked": 10000
    },
    {
      "config": "authority only (\u0394\u226420)",
      "mode": "chatter",
      "pass_through": 10000,
      "policy_block": 10000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 10000
      },
      "pol_passed": 10000,
      "pol_blocked": 10000
    },
    {
      "config": "cum_disp only (\u2264500)",
      "mode": "slow_drift",
      "pass_through": 20,
      "policy_block": 19980,
      "ppm_protect": 0,
      "reasons": {
        "cum_disp": 19980
      },
      "pol_passed": 20,
      "pol_blocked": 19980
    },
    {
      "config": "cum_disp only (\u2264500)",
      "mode": "hug",
      "pass_through": 20000,
      "policy_block": 0,
      "ppm_protect": 0,
      "reasons": {},
      "pol_passed": 20000,
      "pol_blocked": 0
    },
    {
      "config": "cum_disp only (\u2264500)",
      "mode": "chatter",
      "pass_through": 20000,
      "policy_block": 0,
      "ppm_protect": 0,
      "reasons": {},
      "pol_passed": 20000,
      "pol_blocked": 0
    },
    {
      "config": "rate only (\u2264100 / 10 steps)",
      "mode": "slow_drift",
      "pass_through": 4,
      "policy_block": 19996,
      "ppm_protect": 0,
      "reasons": {
        "rate": 19996
      },
      "pol_passed": 4,
      "pol_blocked": 19996
    },
    {
      "config": "rate only (\u2264100 / 10 steps)",
      "mode": "hug",
      "pass_through": 12500,
      "policy_block": 7500,
      "ppm_protect": 0,
      "reasons": {
        "rate": 7500
      },
      "pol_passed": 12500,
      "pol_blocked": 7500
    },
    {
      "config": "rate only (\u2264100 / 10 steps)",
      "mode": "chatter",
      "pass_through": 12500,
      "policy_block": 7500,
      "ppm_protect": 0,
      "reasons": {
        "rate": 7500
      },
      "pol_passed": 12500,
      "pol_blocked": 7500
    },
    {
      "config": "chatter only (\u22648 rev / 20)",
      "mode": "slow_drift",
      "pass_through": 20000,
      "policy_block": 0,
      "ppm_protect": 0,
      "reasons": {},
      "pol_passed": 20000,
      "pol_blocked": 0
    },
    {
      "config": "chatter only (\u22648 rev / 20)",
      "mode": "hug",
      "pass_through": 15386,
      "policy_block": 4614,
      "ppm_protect": 0,
      "reasons": {
        "chatter": 4614
      },
      "pol_passed": 15386,
      "pol_blocked": 4614
    },
    {
      "config": "chatter only (\u22648 rev / 20)",
      "mode": "chatter",
      "pass_through": 15386,
      "policy_block": 4614,
      "ppm_protect": 0,
      "reasons": {
        "chatter": 4614
      },
      "pol_passed": 15386,
      "pol_blocked": 4614
    },
    {
      "config": "authority+cum_disp",
      "mode": "slow_drift",
      "pass_through": 0,
      "policy_block": 20000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 20000
      },
      "pol_passed": 0,
      "pol_blocked": 20000
    },
    {
      "config": "authority+cum_disp",
      "mode": "hug",
      "pass_through": 10000,
      "policy_block": 10000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 10000
      },
      "pol_passed": 10000,
      "pol_blocked": 10000
    },
    {
      "config": "authority+cum_disp",
      "mode": "chatter",
      "pass_through": 10000,
      "policy_block": 10000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 10000
      },
      "pol_passed": 10000,
      "pol_blocked": 10000
    },
    {
      "config": "all four",
      "mode": "slow_drift",
      "pass_through": 0,
      "policy_block": 20000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 20000
      },
      "pol_passed": 0,
      "pol_blocked": 20000
    },
    {
      "config": "all four",
      "mode": "hug",
      "pass_through": 10000,
      "policy_block": 10000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 10000
      },
      "pol_passed": 10000,
      "pol_blocked": 10000
    },
    {
      "config": "all four",
      "mode": "chatter",
      "pass_through": 10000,
      "policy_block": 10000,
      "ppm_protect": 0,
      "reasons": {
        "authority": 10000
      },
      "pol_passed": 10000,
      "pol_blocked": 10000
    }
  ],
  "phase4_redteam.json": {
    "report": [
      {
        "mode": "slow_drift",
        "bare": {
          "prot": 0,
          "pass": 30000,
          "block": 0
        },
        "policy": {
          "prot": 0,
          "pass": 0,
          "block": 30000,
          "reasons": {
            "authority": 30000
          }
        }
      },
      {
        "mode": "hug",
        "bare": {
          "prot": 0,
          "pass": 30000,
          "block": 0
        },
        "policy": {
          "prot": 0,
          "pass": 15000,
          "block": 15000,
          "reasons": {
            "authority": 15000
          }
        }
      },
      {
        "mode": "chatter",
        "bare": {
          "prot": 0,
          "pass": 30000,
          "block": 0
        },
        "policy": {
          "prot": 0,
          "pass": 15000,
          "block": 15000,
          "reasons": {
            "authority": 15000
          }
        }
      },
      {
        "mode": "legit",
        "bare": {
          "prot": 0,
          "pass": 30000,
          "block": 0
        },
        "policy": {
          "prot": 0,
          "pass": 30000,
          "block": 0,
          "reasons": {}
        }
      }
    ],
    "latency_bare_s": 0.08017919200000279,
    "latency_policy_s": 0.04596967400001972,
    "auth": 20,
    "cum": 500,
    "v1_tests_exit": 0
  },
  "threshold_hugging_surface.json": {
    "grid_count": 6600,
    "full_bypass": 6504,
    "full_protect": 96,
    "rule": "For NORMAL priority: delta < threshold (k>=1) => 0% PROTECT always; delta>=threshold (k==0) => 100% PROTECT",
    "max_bypass_path_cell": {
      "threshold": 500,
      "k": 1,
      "delta": 499,
      "n": 10000,
      "alternate": true,
      "protect_count": 0,
      "protect_rate": 0.0,
      "path_length": 4990000,
      "net": 0,
      "full_bypass": true
    },
    "sample_bypass": [
      {
        "threshold": 1,
        "k": 1,
        "delta": 0,
        "n": 100,
        "alternate": true,
        "protect_count": 0,
        "protect_rate": 0.0,
        "path_length": 0,
        "net": 0,
        "full_bypass": true
      },
      {
        "threshold": 1,
        "k": 1,
        "delta": 0,
        "n": 100,
        "alternate": false,
        "protect_count": 0,
        "protect_rate": 0.0,
        "path_length": 0,
        "net": 0,
        "full_bypass": true
      },
      {
        "threshold": 1,
        "k": 1,
        "delta": 0,
        "n": 1000,
        "alternate": true,
        "protect_count": 0,
        "protect_rate": 0.0,
        "path_length": 0,
        "net": 0,
        "full_bypass": true
      }
    ],
    "sample_protect": [
      {
        "threshold": 1,
        "k": 0,
        "delta": 1,
        "n": 100,
        "alternate": true,
        "protect_count": 100,
        "protect_rate": 1.0,
        "path_length": 100,
        "net": 0,
        "full_bypass": false
      },
      {
        "threshold": 1,
        "k": 0,
        "delta": 1,
        "n": 100,
        "alternate": false,
        "protect_count": 100,
        "protect_rate": 1.0,
        "path_length": 100,
        "net": 100,
        "full_bypass": false
      },
      {
        "threshold": 1,
        "k": 0,
        "delta": 1,
        "n": 1000,
        "alternate": true,
        "protect_count": 1000,
        "protect_rate": 1.0,
        "path_length": 1000,
        "net": 0,
        "full_bypass": false
      }
    ]
  }
}
```

---

## 7. Artifact trees

### experiments/
  ai_adversarial_boundary.py (10268 bytes)
  ai_adversarial_research.py (6476 bytes)
  c_harness/Ppm_edge.c (2534 bytes)
  c_harness/Ppm_edge.h (1096 bytes)
  c_harness/adv (16408 bytes)
  c_harness/adversarial_main.c (6233 bytes)
  ext/Ppm_edge.c (2534 bytes)
  ext/Ppm_edge.h (1096 bytes)
  ext/build/lib.linux-x86_64-cpython-312/ppm_ext.cpython-312-x86_64-linux-gnu.so (31536 bytes)
  ext/build/temp.linux-x86_64-cpython-312/Ppm_edge.o (8848 bytes)
  ext/build/temp.linux-x86_64-cpython-312/ppm_ext.o (27456 bytes)
  ext/ppm_ext.c (2626 bytes)
  ext/ppm_ext.cpython-312-x86_64-linux-gnu.so (31536 bytes)
  ext/setup.py (166 bytes)
  multi_seed_differential.py (5797 bytes)
  results/RESEARCH_REPORT.md (5486 bytes)
  results/phase1_bypass_surface.json (9487 bytes)
  results/phase2_adversarial.json (20748 bytes)
  results/phase3_policy_ablation.json (4297 bytes)
  results/phase4_redteam.json (1209 bytes)
  results/threshold_hugging_surface.json (1865 bytes)
  stress_pure_python.py (5449 bytes)

### Ppm_edge_runtime/research/ (local branch content)
  adversarial_policy/PLAN.md (5390 bytes)
  adversarial_policy/PROVENANCE.md (1919 bytes)
  adversarial_policy/README.md (4609 bytes)
  adversarial_policy/generators/ai_adversarial_boundary.py (10268 bytes)
  adversarial_policy/generators/multi_seed_differential.py (5797 bytes)
  adversarial_policy/generators/stress_pure_python.py (5449 bytes)
  adversarial_policy/generators/threshold_hugging_vectors.py (1518 bytes)
  adversarial_policy/harness/Ppm_edge.c (2534 bytes)
  adversarial_policy/harness/Ppm_edge.h (1096 bytes)
  adversarial_policy/harness/c_harness/Ppm_edge.c (2534 bytes)
  adversarial_policy/harness/c_harness/Ppm_edge.h (1096 bytes)
  adversarial_policy/harness/c_harness/adversarial_main.c (6233 bytes)
  adversarial_policy/harness/ppm_ext.c (2626 bytes)
  adversarial_policy/harness/setup.py (166 bytes)
  adversarial_policy/harness/three_way_compare.py (1777 bytes)
  adversarial_policy/policy_layers/min_policy.py (1335 bytes)
  adversarial_policy/reports/RESEARCH_REPORT.md (5486 bytes)
  adversarial_policy/results/phase1_bypass_surface.json (9487 bytes)
  adversarial_policy/results/phase2_adversarial.json (20748 bytes)
  adversarial_policy/results/phase3_policy_ablation.json (4297 bytes)
  adversarial_policy/results/phase4_redteam.json (1209 bytes)

### ppm_edge_runtime_demo_v1/ (extracted V1 zip)
  CMakeLists.txt (432 bytes)
  Examples/Basic.c (857 bytes)
  MASTER_SESSION_RECORD.md (15051 bytes)
  Project.toml (1189 bytes)
  Readme (1478 bytes)
  Src/Ppm_edge/_init_.py (208 bytes)
  Src/Ppm_edge.c (2534 bytes)
  Src/Ppm_edge.h (1096 bytes)
  Tests/Test_demo.py (10197 bytes)
  Tests/Test_import.py (673 bytes)
  Tests/Test_runtime.py (5057 bytes)
  Tests/__pycache__/Test_demo.cpython-312.pyc (13798 bytes)
  Tests/__pycache__/Test_import.cpython-312.pyc (1250 bytes)
  Tests/__pycache__/Test_runtime.cpython-312.pyc (7409 bytes)
  demo/DEMO_EVIDENCE.md (10474 bytes)
  demo/DEMO_SCRIPT.md (4217 bytes)
  demo/README.md (6417 bytes)
  demo/__init__.py (396 bytes)
  demo/__pycache__/__init__.cpython-312.pyc (571 bytes)
  demo/__pycache__/cli.cpython-312.pyc (9691 bytes)
  demo/__pycache__/engine.cpython-312.pyc (4110 bytes)
  demo/__pycache__/events.cpython-312.pyc (2133 bytes)
  demo/__pycache__/evidence.cpython-312.pyc (1971 bytes)
  demo/__pycache__/oracle.cpython-312.pyc (2718 bytes)
  demo/__pycache__/recommender.cpython-312.pyc (3282 bytes)
  demo/__pycache__/render.cpython-312.pyc (4974 bytes)
  demo/__pycache__/streams.cpython-312.pyc (4545 bytes)
  demo/cli.py (7570 bytes)
  demo/engine.py (2953 bytes)
  demo/events.py (1696 bytes)
  demo/evidence.py (2001 bytes)
  demo/fixtures/replay_golden.json (4199 bytes)
  demo/oracle.py (1898 bytes)
  demo/recommender.py (2554 bytes)
  demo/render.py (2785 bytes)
  demo/streams.py (3827 bytes)
  pytest.ini (44 bytes)
  run_demo.py (517 bytes)
  run_tests.py (2552 bytes)
  src/ppm_edge/__init__.py (362 bytes)
  src/ppm_edge/__pycache__/__init__.cpython-312.pyc (519 bytes)
  src/ppm_edge/__pycache__/runtime.cpython-312.pyc (4406 bytes)
  src/ppm_edge/runtime.py (2739 bytes)

---

## 8. GitHub Actions configured (local only)

### ci.yml
- Python 3.11/3.12 pytest on Tests/
- CMake C build + ppm_demo
- Optional V1 zip test job

### research.yml
- research/** branch triggers
- Layout + syntax checks
- Production tests must still pass
- Threshold-hug bypass smoke
- C research harness

---

## 9. Conversation arc (compressed)

1. User: extract files from main → clone + extract V1 zip  
2. Audit vs research history → freeze commits/tags/V2 missing from Git  
3. Regenerate missing work in sandbox only; no production edits  
4. Stress, multi-seed, adversarial contract tests → all PASS  
5. AI-adversarial recommendations → threshold-hug / chatter bypass found  
6. Phases 1–4 policy research → report written  
7. Commit research branch locally; push blocked by GitHub permissions  
8. Configure Actions workflows locally; push still blocked  

---

## 10. How to recover this work

- Sandbox paths under `/home/workdir/artifacts/experiments/` and `Ppm_edge_runtime/research/`
- Local git: branch `research/adversarial-policy-layer` commits `992e9c5`, `fa3b476`
- Push when write access available: `git push -u origin research/adversarial-policy-layer`

END OF EXPORT
