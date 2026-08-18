#!/usr/bin/env python3
"""Phase 18 — Checkpoint / state serialization integrity (harness-only).

Does NOT test or claim findings against the production C kernel.
Builds on Phase 17 hardened recovery model in hardened_policy.py.
"""
from __future__ import annotations

import copy
import json
import random
import sys
from typing import Any, Dict, List, Tuple

from hardened_policy import HardenedConfig, HardenedPolicy

B_GLOBAL = 50_000
SEED = 18
FAILURES: List[Dict[str, Any]] = []
MATRIX: Dict[str, Any] = {}
RESULTS: Dict[str, Any] = {
    "phase": 18,
    "label": "harness-level only — not a claim against production C kernel",
    "config": {"b_global": B_GLOBAL, "seed": SEED},
    "matrix": MATRIX,
    "failures": FAILURES,
    "cases": [],
}


def rec(
    attack: str,
    expected: str,
    actual: str,
    before: Dict[str, Any],
    after: Dict[str, Any],
    state_changed: bool,
    error: str = "",
    passed: bool = True,
) -> None:
    entry = {
        "attack": attack,
        "expected": expected,
        "actual": actual,
        "path_sum_before": before.get("path_sum"),
        "path_sum_after": after.get("path_sum"),
        "origin_budget_before": before.get("origin_budget"),
        "origin_budget_after": after.get("origin_budget"),
        "session_id_before": before.get("session_id"),
        "session_id_after": after.get("session_id"),
        "state_changed": state_changed,
        "error": error,
        "pass": passed,
    }
    RESULTS["cases"].append(entry)
    if not passed:
        FAILURES.append(entry)


def sec(pol: HardenedPolicy) -> Dict[str, Any]:
    return pol.snapshot_security()


def unchanged(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    keys = ("path_sum", "origin_budget", "session_id", "origin", "value", "events_accepted", "origin_updates")
    return all(a.get(k) == b.get(k) for k in keys)


def invariants_ok(pol: HardenedPolicy) -> bool:
    s = pol.state
    if s.path_sum < 0 or s.path_sum > pol.cfg.b_global:
        return False
    if s.origin_budget < 0:
        return False
    if s.session_id < 1:
        return False
    return True


def consume(pol: HardenedPolicy, amount: int) -> None:
    """Consume path budget with small moves + origin rebases as needed."""
    while pol.state.path_sum < amount and pol.state.path_sum < pol.cfg.b_global:
        if abs(pol.state.value + 1 - pol.state.origin) > pol.cfg.cum_disp_limit:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
        ok, _ = pol.try_move(1)
        if not ok:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
            ok, _ = pol.try_move(1)
            if not ok:
                break


def forge_mac(cp: Dict[str, Any], pol: HardenedPolicy) -> Dict[str, Any]:
    out = dict(cp)
    out["mac"] = pol._mac(out)
    return out


# ---------- tests ----------

def test_forged_path_sum() -> bool:
    name = "FORGED_PATH_SUM"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 1000)
    good = pol.create_checkpoint()

    for bad_path in (-1, 0, B_GLOBAL + 1, 10**18, -10**9):
        # For 0: only illegal if current path_sum > 0 (replenish)
        cp = dict(good)
        cp["path_sum"] = bad_path
        cp = forge_mac(cp, pol)
        before = sec(pol)
        accepted, reason = pol.recover_from_checkpoint(cp)
        after = sec(pol)
        should_reject = True
        if bad_path == 0 and before["path_sum"] == 0:
            should_reject = False  # equal path is ok if already 0
        # Our policy rejects path < current (replenish) and path oob
        if bad_path < before["path_sum"] or bad_path < 0 or bad_path > B_GLOBAL:
            should_reject = True
        else:
            should_reject = False

        passed = (not accepted) if should_reject else accepted
        if should_reject and not unchanged(before, after):
            passed = False
        if should_reject and accepted:
            passed = False
        rec(
            f"{name}:{bad_path}",
            "reject" if should_reject else "accept",
            f"{'accept' if accepted else 'reject'}:{reason}",
            before,
            after,
            not unchanged(before, after),
            reason,
            passed,
        )
        if not passed:
            ok = False
        if not invariants_ok(pol):
            ok = False
            rec(f"{name}:invariant", "invariants hold", "broken", before, after, True, "", False)

    MATRIX[name] = {"pass": ok}
    return ok


def test_forged_origin_budget() -> bool:
    name = "FORGED_ORIGIN_BUDGET"
    ok = True
    # Fresh policy per candidate so accepts cannot shrink current budget mid-loop
    for bad_ob in (-1, 0, 10, 11, 10**9, 9):
        pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL, initial_origin_budget=10))
        pol.set_authorized(True)
        pol.update_origin(None)  # budget 10 -> 9
        pol.set_authorized(False)
        good = pol.create_checkpoint()
        current_ob = pol.state.origin_budget  # 9
        cp = dict(good)
        cp["origin_budget"] = bad_ob
        cp = forge_mac(cp, pol)
        before = sec(pol)
        accepted, reason = pol.recover_from_checkpoint(cp)
        after = sec(pol)
        should_reject = bad_ob < 0 or bad_ob > current_ob
        passed = (not accepted) if should_reject else accepted
        if should_reject and not unchanged(before, after):
            passed = False
        rec(
            f"{name}:{bad_ob}",
            "reject" if should_reject else "accept",
            f"{'accept' if accepted else 'reject'}:{reason}",
            before,
            after,
            not unchanged(before, after),
            reason,
            passed,
        )
        if not passed or not invariants_ok(pol):
            ok = False

    MATRIX[name] = {"pass": ok}
    return ok


def test_forged_session_id() -> bool:
    name = "FORGED_SESSION_ID"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 100)
    good = pol.create_checkpoint()
    cur = pol.state.session_id

    candidates = [cur - 1, cur, cur + 1, -1, 0, 10**9, "session", None, 1.5]
    for sid in candidates:
        cp = dict(good)
        cp["session_id"] = sid
        if isinstance(sid, int) and not isinstance(sid, bool):
            cp = forge_mac(cp, pol)
        before = sec(pol)
        accepted, reason = pol.recover_from_checkpoint(cp)
        after = sec(pol)
        should_accept = sid == cur and isinstance(sid, int) and not isinstance(sid, bool)
        passed = accepted if should_accept else (not accepted)
        if not should_accept and not unchanged(before, after):
            passed = False
        rec(
            f"{name}:{sid!r}",
            "accept" if should_accept else "reject",
            f"{'accept' if accepted else 'reject'}:{reason}",
            before,
            after,
            not unchanged(before, after),
            reason,
            passed,
        )
        if not passed or not invariants_ok(pol):
            ok = False

    MATRIX[name] = {"pass": ok}
    return ok


def test_forged_origin() -> bool:
    name = "FORGED_ORIGIN"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 500)
    good = pol.create_checkpoint()
    before = sec(pol)
    cp = dict(good)
    cp["origin"] = before["origin"] + 99999
    cp = forge_mac(cp, pol)
    # Same session, path equal, origin_budget equal — MAC valid after forge_mac
    # Policy currently allows origin change via checkpoint if other checks pass.
    # Security intent: teleporting origin via checkpoint should not increase budget.
    accepted, reason = pol.recover_from_checkpoint(cp)
    after = sec(pol)
    # Path and origin_budget must not improve; session same
    path_ok = after["path_sum"] >= before["path_sum"] and after["path_sum"] <= B_GLOBAL
    ob_ok = after["origin_budget"] <= before["origin_budget"]
    passed = path_ok and ob_ok and invariants_ok(pol)
    # Document whether origin was changed (allowed if MAC+session ok in this model)
    rec(
        name,
        "no budget replenishment; invariants hold",
        f"accepted={accepted} origin {before['origin']}->{after['origin']}",
        before,
        after,
        not unchanged(before, after),
        reason,
        passed,
    )
    if not passed:
        ok = False
    MATRIX[name] = {"pass": ok, "origin_changed": after["origin"] != before["origin"]}
    return ok


def test_forged_value() -> bool:
    name = "FORGED_VALUE"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 200)
    good = pol.create_checkpoint()
    before = sec(pol)
    cp = dict(good)
    cp["value"] = before["value"] + 10_000
    cp = forge_mac(cp, pol)
    accepted, reason = pol.recover_from_checkpoint(cp)
    after = sec(pol)
    path_ok = after["path_sum"] >= before["path_sum"] and after["path_sum"] <= B_GLOBAL
    ob_ok = after["origin_budget"] <= before["origin_budget"]
    passed = path_ok and ob_ok and invariants_ok(pol)
    rec(
        name,
        "no budget replenishment",
        f"accepted={accepted} value {before['value']}->{after['value']}",
        before,
        after,
        not unchanged(before, after),
        reason,
        passed,
    )
    if not passed:
        ok = False
    MATRIX[name] = {"pass": ok}
    return ok


def test_old_checkpoint_replay() -> bool:
    name = "OLD_CHECKPOINT_REPLAY"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 100)
    old_cp = pol.create_checkpoint()
    consume(pol, 5000)  # significant more budget used
    before_loop = sec(pol)
    for i in range(20):
        before = sec(pol)
        accepted, reason = pol.recover_from_checkpoint(old_cp)
        after = sec(pol)
        # Must reject (path replenish) and leave state unchanged
        passed = (not accepted) and unchanged(before, after) and reason == "cp_path_replenish"
        rec(
            f"{name}:{i}",
            "reject cp_path_replenish; state unchanged",
            f"{'accept' if accepted else 'reject'}:{reason}",
            before,
            after,
            not unchanged(before, after),
            reason,
            passed,
        )
        if not passed:
            ok = False
    if before_loop["path_sum"] != pol.state.path_sum:
        ok = False
    MATRIX[name] = {"pass": ok, "path_sum": pol.state.path_sum}
    return ok


def test_cross_session_checkpoint() -> bool:
    name = "CROSS_SESSION_CHECKPOINT"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 100)
    cp_a = pol.create_checkpoint()
    # New session
    pol.advance_session()
    before = sec(pol)
    accepted, reason = pol.recover_from_checkpoint(cp_a)
    after = sec(pol)
    passed = (not accepted) and unchanged(before, after) and reason == "cp_session_mismatch"
    rec(
        name,
        "reject cp_session_mismatch; state unchanged",
        f"{'accept' if accepted else 'reject'}:{reason}",
        before,
        after,
        not unchanged(before, after),
        reason,
        passed,
    )
    if not passed:
        ok = False
    MATRIX[name] = {"pass": ok}
    return ok


def test_malformed_checkpoints() -> bool:
    name = "MALFORMED_CHECKPOINTS"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 50)
    good = pol.create_checkpoint()

    malformed = [
        None,
        "not-a-dict",
        123,
        1.5,
        [],
        ["path_sum", 0],
        {},
        {**good, "path_sum": None},
        {**good, "path_sum": "100"},
        {**good, "path_sum": 1.5},
        {**good, "path_sum": [1]},
        {**good, "path_sum": {"x": 1}},
        {**good, "origin_budget": True},  # bool is int subclass — we reject bool
        {k: v for k, v in good.items() if k != "mac"},  # missing mac
        {k: v for k, v in good.items() if k != "path_sum"},
        {**good, "mac": 12345},
        {**good, "mac": "deadbeef"},  # wrong mac
        {**good, "extra_field": "ignored"},  # extra ok if mac still matches core
    ]

    for i, cp in enumerate(malformed):
        before = sec(pol)
        # Recompute mac only for the extra_field case so it can be valid
        if isinstance(cp, dict) and "extra_field" in cp and "mac" in cp:
            cp = forge_mac(cp, pol)
        accepted, reason = pol.recover_from_checkpoint(cp)
        after = sec(pol)
        # extra_field with valid mac and same security fields should accept
        is_extra_only = isinstance(cp, dict) and "extra_field" in cp and cp.get("path_sum") == good["path_sum"]
        should_accept = is_extra_only
        passed = accepted if should_accept else (not accepted)
        if not should_accept and not unchanged(before, after):
            passed = False
        rec(
            f"{name}:{i}",
            "accept" if should_accept else "reject; state unchanged",
            f"{'accept' if accepted else 'reject'}:{reason}",
            before,
            after,
            not unchanged(before, after),
            reason,
            passed,
        )
        if not passed or not invariants_ok(pol):
            ok = False

    MATRIX[name] = {"pass": ok}
    return ok


def test_serialization_round_trip() -> bool:
    name = "SERIALIZATION_ROUND_TRIP"
    ok = True
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    consume(pol, 1234)
    pol.set_authorized(True)
    pol.update_origin(None)
    pol.set_authorized(False)
    before = sec(pol)
    cp = pol.create_checkpoint()
    # Serialize through JSON
    blob = json.dumps(cp)
    restored = json.loads(blob)
    accepted, reason = pol.recover_from_checkpoint(restored)
    after = sec(pol)
    passed = accepted and after["path_sum"] == before["path_sum"] and after["origin_budget"] == before["origin_budget"]
    passed = passed and after["session_id"] == before["session_id"] and invariants_ok(pol)
    rec(
        name,
        "accept identical security state",
        f"{'accept' if accepted else 'reject'}:{reason}",
        before,
        after,
        not unchanged(before, after),
        reason,
        passed,
    )
    if not passed:
        ok = False
    MATRIX[name] = {"pass": ok}
    return ok


def test_randomized_tampering() -> bool:
    name = "RANDOMIZED_TAMPERING"
    rng = random.Random(SEED)
    pol = HardenedPolicy(HardenedConfig(b_global=B_GLOBAL))
    ok = True
    checkpoints: List[Dict[str, Any]] = []
    N = 10_000

    for i in range(N):
        before = sec(pol)
        choice = rng.randrange(8)
        if choice == 0:
            # valid move
            d = rng.choice([-1, 1, 2, -2])
            if abs(pol.state.value + d - pol.state.origin) > pol.cfg.cum_disp_limit:
                pol.set_authorized(True)
                pol.update_origin(None)
                pol.set_authorized(False)
            pol.try_move(d)
        elif choice == 1:
            checkpoints.append(pol.create_checkpoint())
        elif choice == 2:
            if checkpoints:
                pol.recover_from_checkpoint(checkpoints[-1])
        elif choice == 3:
            # old checkpoint replay
            if len(checkpoints) > 1:
                pol.recover_from_checkpoint(checkpoints[0])
        elif choice == 4:
            # forged
            if checkpoints:
                fake = dict(checkpoints[-1])
                fake["path_sum"] = rng.choice([-1, 0, B_GLOBAL + 1, before["path_sum"] - 1])
                fake = forge_mac(fake, pol)
                pol.recover_from_checkpoint(fake)
        elif choice == 5:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
        elif choice == 6:
            pol.reauth()
        else:
            # recovery attempt with malformed
            pol.recover_from_checkpoint(rng.choice([None, "x", {}, {"path_sum": "bad"}]))

        after = sec(pol)
        if after["path_sum"] < before["path_sum"]:
            rec(f"{name}:{i}", "path non-decreasing", f"path {before['path_sum']}->{after['path_sum']}", before, after, True, "", False)
            ok = False
        if after["origin_budget"] > before["origin_budget"]:
            # reauth must not increase origin_budget; only explicit grant would — we don't have grant
            rec(f"{name}:{i}", "origin_budget not increased", f"ob {before['origin_budget']}->{after['origin_budget']}", before, after, True, "", False)
            ok = False
        if after["session_id"] < before["session_id"]:
            rec(f"{name}:{i}", "session_id not backward", f"sid {before['session_id']}->{after['session_id']}", before, after, True, "", False)
            ok = False
        if not invariants_ok(pol):
            rec(f"{name}:{i}", "invariants", "broken", before, after, True, "", False)
            ok = False

    MATRIX[name] = {"pass": ok, "operations": N, "seed": SEED, "final_path": pol.state.path_sum}
    return ok


def main() -> int:
    print(f"=== PHASE 18 State Integrity (harness-only)  B_global={B_GLOBAL} ===\n")
    print("NOTE: Results are harness-level only. Not a claim against production C kernel.\n")

    tests = [
        ("FORGED_PATH_SUM", test_forged_path_sum),
        ("FORGED_ORIGIN_BUDGET", test_forged_origin_budget),
        ("FORGED_SESSION_ID", test_forged_session_id),
        ("FORGED_ORIGIN", test_forged_origin),
        ("FORGED_VALUE", test_forged_value),
        ("OLD_CHECKPOINT_REPLAY", test_old_checkpoint_replay),
        ("CROSS_SESSION_CHECKPOINT", test_cross_session_checkpoint),
        ("MALFORMED_CHECKPOINTS", test_malformed_checkpoints),
        ("SERIALIZATION_ROUND_TRIP", test_serialization_round_trip),
        ("RANDOMIZED_TAMPERING", test_randomized_tampering),
    ]

    all_pass = True
    for label, fn in tests:
        print(f"Running {label}...", flush=True)
        try:
            passed = fn()
        except Exception as e:
            passed = False
            MATRIX[label] = {"pass": False, "error": str(e)}
            rec(label, "no exception", str(e), {}, {}, True, str(e), False)
            print(f"  ERROR: {e}")
        print(f"  {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_pass = False

    RESULTS["all_pass"] = all_pass
    RESULTS["failure_count"] = len(FAILURES)

    print("\n=== PASS/FAIL MATRIX ===")
    for label, _ in tests:
        m = MATRIX.get(label, {})
        print(f"  {'PASS' if m.get('pass') else 'FAIL'}: {label}")
    print(f"\nALL_PASS={all_pass}  failures_recorded={len(FAILURES)}")

    out = "/home/workdir/artifacts/phase18/PHASE_18_RESULTS.json"
    with open(out, "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"Results → {out}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
