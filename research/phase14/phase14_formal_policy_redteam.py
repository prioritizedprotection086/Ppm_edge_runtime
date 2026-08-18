#!/usr/bin/env python3
"""Phase 14 – FormalPolicy + non-replenishable B_global red team.

Re-runs Phase 13 attacks and adds honest-traffic / budget-survival probes.
Production kernel: FROZEN.
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple

from formal_policy_bglobal import FormalPolicy, PolicyConfig

AUTH = 20
CUM = 500
B_GLOBAL = 100_000


def run_attack(
    name: str,
    cfg: PolicyConfig,
    steps: List[Tuple],
    authorized: bool = True,
) -> Dict[str, Any]:
    pol = FormalPolicy(cfg, origin=0, last=0)
    pol.set_authorized(authorized)
    for step in steps:
        kind = step[0]
        if kind == "move":
            delta = step[1]
            target = pol.state.last_accepted + delta
            pol.try_accept(target)
        elif kind == "reset_origin":
            pol.update_origin(None)
        elif kind == "set_auth":
            pol.set_authorized(step[1])
        elif kind == "full_reset":
            pol.full_reset(step[1] if len(step) > 1 else 0)
    snap = pol.snapshot()
    return {
        "name": name,
        "final_path": snap["state"]["total_path"],
        "origin_updates": snap["state"]["origin_updates"],
        "events_accepted": snap["state"]["events_accepted"],
        "events_rejected": snap["state"]["events_rejected"],
        "max_excursion": snap["state"]["max_excursion"],
        "block_reasons": snap["state"]["block_reasons"],
        "final_origin": snap["state"]["origin"],
        "final_value": snap["state"]["last_accepted"],
        "fingerprint": pol.fingerprint(),
        "path_at_or_under_budget": snap["state"]["total_path"] <= cfg.b_global,
    }


def main() -> Dict[str, Any]:
    cfg = PolicyConfig(
        authority_delta=AUTH,
        cum_disp_limit=CUM,
        b_global=B_GLOBAL,
        origin_update_requires_auth=True,
        origin_update_cost=0,
        allow_origin_reset_to_current=True,
        allow_full_reset=False,
        full_reset_clears_path=False,
    )
    report: Dict[str, Any] = {
        "phase": 14,
        "config": {
            "authority_delta": AUTH,
            "cum_disp_limit": CUM,
            "b_global": B_GLOBAL,
            "origin_update_requires_auth": True,
            "origin_update_cost": 0,
            "allow_origin_reset_to_current": True,
            "allow_full_reset": False,
            "full_reset_clears_path": False,
        },
        "attacks": [],
        "honest": [],
        "pass_fail": {},
    }

    print(f"=== PHASE 14  B_global={B_GLOBAL}  AUTH={AUTH}  CUM={CUM} ===\n")

    # ---- Attack 1: fixed origin oscillation (path should stop at B_global) ----
    steps = []
    for i in range(10_000):
        steps.append(("move", AUTH - 1 if i % 2 == 0 else -(AUTH - 1)))
    r = run_attack("fixed_origin_oscillation_10k", cfg, steps, authorized=False)
    report["attacks"].append(r)
    report["pass_fail"][r["name"]] = r["final_path"] <= B_GLOBAL and (
        r["block_reasons"].get("b_global", 0) > 0 or r["final_path"] == B_GLOBAL
        or r["events_accepted"] * (AUTH - 1) <= B_GLOBAL
    )
    print(f"[1] {r['name']}: path={r['final_path']} accepted={r['events_accepted']} "
          f"rejected={r['events_rejected']} reasons={r['block_reasons']}")

    # ---- Attack 2: min-cost origin replenish ----
    steps = []
    for i in range(2000):
        steps.append(("move", AUTH - 1))
        steps.append(("reset_origin",))
    r = run_attack("min_cost_origin_2000", cfg, steps, authorized=True)
    report["attacks"].append(r)
    report["pass_fail"][r["name"]] = r["final_path"] <= B_GLOBAL
    print(f"[2] {r['name']}: path={r['final_path']} origins={r['origin_updates']} "
          f"rejected={r['events_rejected']} reasons={r['block_reasons']}")

    # ---- Attack 3: full-budget replenish (Phase 13 killer) ----
    steps = []
    for i in range(200):
        remaining = CUM
        while remaining >= AUTH - 1:
            steps.append(("move", AUTH - 1))
            remaining -= AUTH - 1
        steps.append(("reset_origin",))
    r = run_attack("full_budget_replenish_200", cfg, steps, authorized=True)
    report["attacks"].append(r)
    # MUST be capped — this is the critical Phase 14 criterion
    report["pass_fail"][r["name"]] = r["final_path"] <= B_GLOBAL and r["block_reasons"].get("b_global", 0) > 0
    print(f"[3] {r['name']}: path={r['final_path']} origins={r['origin_updates']} "
          f"rejected={r['events_rejected']} reasons={r['block_reasons']} "
          f"CRITICAL_CAP={'YES' if report['pass_fail'][r['name']] else 'NO'}")

    # ---- Attack 4: origin denied ----
    steps = []
    for i in range(2000):
        steps.append(("move", AUTH - 1))
        steps.append(("reset_origin",))
    r = run_attack("origin_denied_2000", cfg, steps, authorized=False)
    report["attacks"].append(r)
    report["pass_fail"][r["name"]] = r["final_path"] <= CUM and r["origin_updates"] == 0
    print(f"[4] {r['name']}: path={r['final_path']} origins={r['origin_updates']} "
          f"rejected={r['events_rejected']} reasons={r['block_reasons']}")

    # ---- Attack 5: tiny chatter ----
    steps = []
    for i in range(150_000):
        steps.append(("move", 1 if (i % 2 == 0) else -1))
    r = run_attack("tiny_chatter_150k", cfg, steps, authorized=False)
    report["attacks"].append(r)
    report["pass_fail"][r["name"]] = r["final_path"] <= B_GLOBAL
    print(f"[5] {r['name']}: path={r['final_path']} accepted={r['events_accepted']} "
          f"rejected={r['events_rejected']} reasons={r['block_reasons']}")

    # ---- Attack 6: authority violation ----
    steps = [("move", AUTH), ("move", AUTH + 1), ("move", AUTH - 1)]
    r = run_attack("authority_violation", cfg, steps, authorized=False)
    report["attacks"].append(r)
    report["pass_fail"][r["name"]] = r["block_reasons"].get("authority", 0) >= 1
    print(f"[6] {r['name']}: accepted={r['events_accepted']} rejected={r['events_rejected']} "
          f"reasons={r['block_reasons']}")

    # ---- Attack 7: spatial violation ----
    steps = []
    for _ in range(40):
        steps.append(("move", AUTH - 1))
    r = run_attack("spatial_violation", cfg, steps, authorized=False)
    report["attacks"].append(r)
    report["pass_fail"][r["name"]] = r["block_reasons"].get("cum_disp", 0) > 0
    print(f"[7] {r['name']}: path={r['final_path']} rejected={r['events_rejected']} "
          f"reasons={r['block_reasons']}")

    # ---- Honest A: short walk under budget ----
    steps = [("move", 5), ("move", -3), ("move", 8), ("move", -4)]
    r = run_attack("honest_short_walk", cfg, steps, authorized=False)
    report["honest"].append(r)
    report["pass_fail"][r["name"]] = r["events_rejected"] == 0
    print(f"[H1] {r['name']}: path={r['final_path']} rejected={r['events_rejected']}")

    # ---- Honest B: a few authorized origin updates, total path << B ----
    steps = []
    for _ in range(10):
        steps.append(("move", 10))
        steps.append(("reset_origin",))
    r = run_attack("honest_origin_rebase_10", cfg, steps, authorized=True)
    report["honest"].append(r)
    report["pass_fail"][r["name"]] = r["events_rejected"] == 0 and r["origin_updates"] == 10
    print(f"[H2] {r['name']}: path={r['final_path']} origins={r['origin_updates']} "
          f"rejected={r['events_rejected']}")

    # ---- Honest C: near-budget careful walk then stop ----
    steps = []
    # 5000 * 19 = 95000 < 100000
    for i in range(5000):
        steps.append(("move", AUTH - 1 if i % 2 == 0 else -(AUTH - 1)))
    r = run_attack("honest_near_budget_oscillation", cfg, steps, authorized=False)
    report["honest"].append(r)
    report["pass_fail"][r["name"]] = r["events_rejected"] == 0 and r["final_path"] <= B_GLOBAL
    print(f"[H3] {r['name']}: path={r['final_path']} rejected={r['events_rejected']}")

    # ---- Survival: exhaust budget, re-auth, try continue ----
    steps = []
    for i in range(6000):
        steps.append(("move", AUTH - 1 if i % 2 == 0 else -(AUTH - 1)))
    steps.append(("set_auth", True))
    for i in range(100):
        steps.append(("move", AUTH - 1 if i % 2 == 0 else -(AUTH - 1)))
    r = run_attack("budget_survives_reauth", cfg, steps, authorized=False)
    report["attacks"].append(r)
    report["pass_fail"][r["name"]] = r["final_path"] <= B_GLOBAL and r["block_reasons"].get("b_global", 0) > 0
    print(f"[S1] {r['name']}: path={r['final_path']} rejected={r['events_rejected']} "
          f"reasons={r['block_reasons']}")

    # Summary
    print("\n=== PASS/FAIL ===")
    all_ok = True
    for k, v in report["pass_fail"].items():
        mark = "PASS" if v else "FAIL"
        if not v:
            all_ok = False
        print(f"  {mark}: {k}")
    report["all_pass"] = all_ok
    print(f"\nALL_PASS={all_ok}")

    out = "/home/workdir/artifacts/phase14/PHASE_14_RESULTS.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nResults → {out}")
    return report


if __name__ == "__main__":
    main()
