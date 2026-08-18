#!/usr/bin/env python3
"""Phase 15 — Adversarial budget / accounting invariants.

Harness-only. Production PPM-Edge kernel is NEVER modified.
Builds on Phase 14 FormalPolicy with non-replenishable B_global.
"""
from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from formal_policy_bglobal import FormalPolicy, PolicyConfig, PolicyState

B_GLOBAL = 100_000
AUTH = 20
CUM = 500
INT32_MAX = 2**31 - 1
INT32_MIN = -(2**31)
SEED = 42

FAILURES: List[Dict[str, Any]] = []
RESULTS: Dict[str, Any] = {
    "phase": 15,
    "config": {
        "b_global": B_GLOBAL,
        "authority_delta": AUTH,
        "cum_disp_limit": CUM,
        "seed": SEED,
    },
    "matrix": {},
    "failures": FAILURES,
}


def cfg(**kwargs) -> PolicyConfig:
    base = dict(
        authority_delta=AUTH,
        cum_disp_limit=CUM,
        b_global=B_GLOBAL,
        origin_update_requires_auth=True,
        origin_update_cost=0,
        allow_origin_reset_to_current=True,
        allow_full_reset=True,  # enable for recovery tests; path not cleared
        full_reset_clears_path=False,
    )
    base.update(kwargs)
    return PolicyConfig(**base)


def snapshot_accounting(pol: FormalPolicy) -> Dict[str, Any]:
    return {
        "total_path": pol.state.total_path,
        "origin": pol.state.origin,
        "last_accepted": pol.state.last_accepted,
        "events_accepted": pol.state.events_accepted,
        "origin_updates": pol.state.origin_updates,
        "remaining": B_GLOBAL - pol.state.total_path
        if pol.cfg.b_global == B_GLOBAL
        else pol.cfg.b_global - pol.state.total_path,
    }


def record_failure(
    test: str,
    index: int,
    prev: Dict[str, Any],
    op: str,
    result_state: Dict[str, Any],
    expected: str,
    actual: str,
) -> None:
    FAILURES.append(
        {
            "test": test,
            "operation_index": index,
            "previous_state": prev,
            "attempted_operation": op,
            "resulting_state": result_state,
            "expected": expected,
            "actual": actual,
        }
    )


def assert_invariants(pol: FormalPolicy, test: str, index: int, op: str, prev: Dict[str, Any]) -> bool:
    """Core accounting invariants after every operation."""
    ok = True
    bg = pol.cfg.b_global
    path = pol.state.total_path
    if path < 0:
        record_failure(test, index, prev, op, snapshot_accounting(pol), "path_sum >= 0", f"path_sum={path}")
        ok = False
    if path > bg:
        record_failure(
            test, index, prev, op, snapshot_accounting(pol), f"path_sum <= {bg}", f"path_sum={path}"
        )
        ok = False
    if path < prev["total_path"]:
        record_failure(
            test,
            index,
            prev,
            op,
            snapshot_accounting(pol),
            "path_sum non-decreasing",
            f"path_sum {prev['total_path']} -> {path}",
        )
        ok = False
    remaining = bg - path
    if remaining != bg - path:
        ok = False
    return ok


def run_exact_boundary() -> bool:
    name = "EXACT_BOUNDARY"
    pol = FormalPolicy(cfg(), origin=0, last=0)
    pol.set_authorized(False)
    ok = True
    # Consume exactly B_global with delta=1 oscillations (within auth & spatial)
    # Spatial limit is 500 — stay near origin by oscillating ±1
    path_target = B_GLOBAL
    i = 0
    while pol.state.total_path < path_target:
        prev = snapshot_accounting(pol)
        # alternate +1 / -1 but when near spatial edge, only step toward origin
        if pol.state.last_accepted >= 1:
            delta = -1
        else:
            delta = 1
        # remaining budget
        rem = B_GLOBAL - pol.state.total_path
        if rem <= 0:
            break
        if rem < abs(delta):
            # would overshoot — stop pre-boundary for exact fill via partial
            break
        target = pol.state.last_accepted + delta
        accepted, reason = pol.try_accept(target)
        if not assert_invariants(pol, name, i, f"move({delta})", prev):
            ok = False
        if not accepted:
            # unexpected reject before filling
            if pol.state.total_path < B_GLOBAL:
                record_failure(
                    name,
                    i,
                    prev,
                    f"move({delta})",
                    snapshot_accounting(pol),
                    "accept until boundary",
                    f"rejected:{reason}",
                )
                ok = False
            break
        i += 1
        if i > B_GLOBAL + 10:
            record_failure(name, i, prev, "loop", snapshot_accounting(pol), "terminate", "infinite loop")
            ok = False
            break

    # Force exact fill if we're short due to step size
    while pol.state.total_path < B_GLOBAL:
        prev = snapshot_accounting(pol)
        rem = B_GLOBAL - pol.state.total_path
        # use delta=1 toward open space if possible
        if abs(pol.state.last_accepted + 1 - pol.state.origin) <= CUM and 1 <= AUTH:
            target = pol.state.last_accepted + 1
        elif abs(pol.state.last_accepted - 1 - pol.state.origin) <= CUM:
            target = pol.state.last_accepted - 1
        else:
            # rebase origin to continue filling (authorized)
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
            continue
        accepted, reason = pol.try_accept(target)
        if not assert_invariants(pol, name, i, f"move_to({target})", prev):
            ok = False
        if not accepted:
            break
        i += 1

    at_boundary = pol.state.total_path == B_GLOBAL
    if not at_boundary and pol.state.total_path > B_GLOBAL:
        ok = False
        record_failure(
            name, i, {}, "boundary", snapshot_accounting(pol), f"path=={B_GLOBAL}", f"path={pol.state.total_path}"
        )

    # Next positive-cost move must reject; path unchanged
    prev = snapshot_accounting(pol)
    path_before = pol.state.total_path
    # ensure we can propose a legal auth/spatial move that costs path
    pol.set_authorized(True)
    pol.update_origin(None)  # origin to current — does not reset path
    pol.set_authorized(False)
    accepted, reason = pol.try_accept(pol.state.last_accepted + 1)
    if accepted or reason != "b_global":
        record_failure(
            name,
            i + 1,
            prev,
            "move(+1) after boundary",
            snapshot_accounting(pol),
            "reject with b_global",
            f"accepted={accepted} reason={reason}",
        )
        ok = False
    if pol.state.total_path != path_before:
        record_failure(
            name,
            i + 1,
            prev,
            "move(+1) after boundary",
            snapshot_accounting(pol),
            f"path unchanged ({path_before})",
            f"path={pol.state.total_path}",
        )
        ok = False
    if not assert_invariants(pol, name, i + 1, "post-boundary", prev):
        ok = False

    RESULTS["matrix"][name] = {
        "pass": ok and pol.state.total_path == B_GLOBAL,
        "path_sum": pol.state.total_path,
        "at_boundary": pol.state.total_path == B_GLOBAL,
        "next_rejected": not accepted and reason == "b_global",
    }
    return RESULTS["matrix"][name]["pass"]


def run_overshoot() -> bool:
    name = "OVERSHOOT"
    pol = FormalPolicy(cfg(), origin=0, last=0)
    ok = True
    # Fill to B_global - 5
    target_path = B_GLOBAL - 5
    while pol.state.total_path < target_path:
        prev = snapshot_accounting(pol)
        rem = target_path - pol.state.total_path
        step = min(1, rem)
        if abs(pol.state.last_accepted + step - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
            continue
        pol.try_accept(pol.state.last_accepted + step)
        if not assert_invariants(pol, name, 0, "fill", prev):
            ok = False

    prev = snapshot_accounting(pol)
    path_before = pol.state.total_path
    # Attempt move of +10 which would exceed
    accepted, reason = pol.try_accept(pol.state.last_accepted + 10)
    if accepted:
        record_failure(
            name, 1, prev, "move(+10)", snapshot_accounting(pol), "reject", "accepted"
        )
        ok = False
    if reason != "b_global" and reason != "authority":
        # authority also ok if delta>AUTH; use smaller overshoot within AUTH
        pass
    # Retry with delta that is within AUTH but exceeds budget
    rem = B_GLOBAL - path_before
    delta = rem + 1  # would exceed by 1
    if delta > AUTH:
        # fill closer first
        while B_GLOBAL - pol.state.total_path > AUTH:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
            pol.try_accept(pol.state.last_accepted + 1)
        path_before = pol.state.total_path
        delta = (B_GLOBAL - path_before) + 1
        if delta > AUTH:
            delta = AUTH  # still may reject on b_global if rem < AUTH

    prev = snapshot_accounting(pol)
    path_before = pol.state.total_path
    if abs(pol.state.last_accepted + delta - pol.state.origin) > CUM:
        pol.set_authorized(True)
        pol.update_origin(None)
        pol.set_authorized(False)
    accepted, reason = pol.try_accept(pol.state.last_accepted + delta)
    if accepted:
        record_failure(name, 2, prev, f"move(+{delta})", snapshot_accounting(pol), "reject", "accepted")
        ok = False
    if pol.state.total_path != path_before:
        record_failure(
            name,
            2,
            prev,
            f"move(+{delta})",
            snapshot_accounting(pol),
            f"path unchanged {path_before}",
            f"path={pol.state.total_path}",
        )
        ok = False
    if reason != "b_global":
        record_failure(
            name, 2, prev, f"move(+{delta})", snapshot_accounting(pol), "reason=b_global", f"reason={reason}"
        )
        ok = False
    if not assert_invariants(pol, name, 2, f"move(+{delta})", prev):
        ok = False

    RESULTS["matrix"][name] = {
        "pass": ok,
        "path_unchanged_on_reject": pol.state.total_path == path_before,
        "reject_reason": reason,
    }
    return ok


def run_rejected_move_accounting() -> bool:
    name = "REJECTED_MOVE_ACCOUNTING"
    pol = FormalPolicy(cfg(), origin=0, last=0)
    ok = True
    # Fill until remaining budget is in [1, AUTH]
    while B_GLOBAL - pol.state.total_path > AUTH:
        if abs(pol.state.last_accepted + 1 - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
        prev = snapshot_accounting(pol)
        pol.try_accept(pol.state.last_accepted + 1)
        if not assert_invariants(pol, name, 0, "fill", prev):
            ok = False

    # Consume remaining exactly down to 0 if possible with unit steps
    while B_GLOBAL - pol.state.total_path > 0:
        rem = B_GLOBAL - pol.state.total_path
        step = 1
        if abs(pol.state.last_accepted + step - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
        prev = snapshot_accounting(pol)
        accepted, _ = pol.try_accept(pol.state.last_accepted + step)
        if not accepted:
            break
        if not assert_invariants(pol, name, 0, "exact_fill", prev):
            ok = False

    path_before = pol.state.total_path
    if path_before != B_GLOBAL:
        # still try overshoot from current
        pass

    for i in range(500):
        prev = snapshot_accounting(pol)
        path_before = pol.state.total_path
        # Always attempt a move that would increase path by at least 1 past budget
        delta = 1
        if abs(pol.state.last_accepted + delta - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
            if pol.state.total_path != path_before:
                record_failure(
                    name,
                    i,
                    prev,
                    "origin_update",
                    snapshot_accounting(pol),
                    f"path={path_before}",
                    f"path={pol.state.total_path}",
                )
                ok = False
                path_before = pol.state.total_path
        accepted, reason = pol.try_accept(pol.state.last_accepted + delta)
        if accepted:
            record_failure(name, i, prev, f"move(+{delta})", snapshot_accounting(pol), "reject", "accepted")
            ok = False
        if pol.state.total_path != path_before:
            record_failure(
                name,
                i,
                prev,
                f"move(+{delta})",
                snapshot_accounting(pol),
                f"path unchanged {path_before}",
                f"path={pol.state.total_path}",
            )
            ok = False
        if reason not in ("b_global", "authority", "cum_disp"):
            record_failure(
                name, i, prev, f"move(+{delta})", snapshot_accounting(pol), "reject reason", f"reason={reason}"
            )
            ok = False
        if not assert_invariants(pol, name, i, f"move(+{delta})", prev):
            ok = False

    RESULTS["matrix"][name] = {
        "pass": ok and pol.state.total_path == path_before,
        "path_sum": pol.state.total_path,
        "reject_count": 500,
    }
    return RESULTS["matrix"][name]["pass"]


def run_origin_update_loop() -> bool:
    name = "ORIGIN_UPDATE_LOOP"
    pol = FormalPolicy(cfg(), origin=0, last=0)
    pol.set_authorized(True)
    ok = True
    # Consume some path first
    for _ in range(100):
        pol.try_accept(pol.state.last_accepted + 1)
        if abs(pol.state.last_accepted - pol.state.origin) > CUM - 2:
            pol.update_origin(None)
    path_after_moves = pol.state.total_path

    for i in range(3000):
        prev = snapshot_accounting(pol)
        pol.update_origin(None)
        if pol.state.total_path != path_after_moves and pol.state.total_path != prev["total_path"]:
            # path should only stay same (origin_update_cost=0)
            if pol.state.total_path < prev["total_path"]:
                record_failure(
                    name,
                    i,
                    prev,
                    "origin_update",
                    snapshot_accounting(pol),
                    "path non-decreasing / no reset",
                    f"path {prev['total_path']} -> {pol.state.total_path}",
                )
                ok = False
        if not assert_invariants(pol, name, i, "origin_update", prev):
            ok = False
        # attempt a move that costs path if room
        prev2 = snapshot_accounting(pol)
        if pol.state.total_path < B_GLOBAL:
            pol.try_accept(pol.state.last_accepted + 1)
            if not assert_invariants(pol, name, i, "move(+1)", prev2):
                ok = False

    if pol.state.total_path > B_GLOBAL:
        ok = False
        record_failure(
            name, 9999, {}, "final", snapshot_accounting(pol), f"path<={B_GLOBAL}", f"path={pol.state.total_path}"
        )

    RESULTS["matrix"][name] = {
        "pass": ok,
        "final_path": pol.state.total_path,
        "origin_updates": pol.state.origin_updates,
    }
    return ok


def run_reauth_loop() -> bool:
    name = "REAUTH_LOOP"
    pol = FormalPolicy(cfg(), origin=0, last=0)
    ok = True
    # Consume half budget
    while pol.state.total_path < B_GLOBAL // 2:
        if abs(pol.state.last_accepted + 1 - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
        pol.try_accept(pol.state.last_accepted + 1)

    path_mid = pol.state.total_path
    for i in range(200):
        prev = snapshot_accounting(pol)
        pol.set_authorized(True)
        pol.set_authorized(False)
        if pol.state.total_path != prev["total_path"]:
            record_failure(
                name,
                i,
                prev,
                "reauth",
                snapshot_accounting(pol),
                "path unchanged on reauth",
                f"path {prev['total_path']} -> {pol.state.total_path}",
            )
            ok = False
        # continue moving
        if abs(pol.state.last_accepted + 1 - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
        prev2 = snapshot_accounting(pol)
        pol.try_accept(pol.state.last_accepted + 1)
        if not assert_invariants(pol, name, i, "move after reauth", prev2):
            ok = False

    if pol.state.total_path < path_mid:
        ok = False
        record_failure(
            name, 999, {}, "final", snapshot_accounting(pol), f"path >= {path_mid}", f"path={pol.state.total_path}"
        )

    RESULTS["matrix"][name] = {
        "pass": ok,
        "path_mid": path_mid,
        "final_path": pol.state.total_path,
        "monotonic": pol.state.total_path >= path_mid,
    }
    return ok


def run_recovery_loop() -> bool:
    name = "RECOVERY_LOOP"
    pol = FormalPolicy(cfg(allow_full_reset=True, full_reset_clears_path=False), origin=0, last=0)
    ok = True
    while pol.state.total_path < B_GLOBAL // 3:
        if abs(pol.state.last_accepted + 1 - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
        pol.try_accept(pol.state.last_accepted + 1)

    path_mid = pol.state.total_path
    for i in range(50):
        prev = snapshot_accounting(pol)
        pol.full_reset(0)
        if pol.state.total_path != path_mid and pol.state.total_path != prev["total_path"]:
            if pol.state.total_path < prev["total_path"]:
                record_failure(
                    name,
                    i,
                    prev,
                    "full_reset",
                    snapshot_accounting(pol),
                    "path not cleared by recovery",
                    f"path {prev['total_path']} -> {pol.state.total_path}",
                )
                ok = False
                path_mid = pol.state.total_path  # continue from actual
        if not assert_invariants(pol, name, i, "full_reset", prev):
            ok = False
        # try move after recovery
        prev2 = snapshot_accounting(pol)
        accepted, reason = pol.try_accept(1)
        if not assert_invariants(pol, name, i, "move after recovery", prev2):
            ok = False

    RESULTS["matrix"][name] = {
        "pass": ok,
        "path_mid": path_mid,
        "final_path": pol.state.total_path,
        "path_preserved_across_reset": pol.state.total_path >= path_mid,
    }
    return ok


def run_integer_edge_values() -> bool:
    name = "INTEGER_EDGE_VALUES"
    ok = True
    edges = [0, 1, B_GLOBAL - 1, B_GLOBAL, B_GLOBAL + 1, INT32_MAX, INT32_MIN, AUTH, -AUTH, AUTH - 1, -(AUTH - 1)]

    # Policy with huge spatial so authority/spatial don't mask b_global
    pol = FormalPolicy(
        cfg(cum_disp_limit=INT32_MAX // 2, authority_delta=INT32_MAX // 4, b_global=B_GLOBAL),
        origin=0,
        last=0,
    )
    # Bring path near budget with safe steps
    while pol.state.total_path < B_GLOBAL - 10:
        prev = snapshot_accounting(pol)
        step = min(AUTH, B_GLOBAL - 10 - pol.state.total_path)
        if step <= 0:
            break
        # use small steps only — authority_delta is huge so ok
        step = min(step, 10)
        pol.cfg.authority_delta = max(pol.cfg.authority_delta, step)
        pol.try_accept(pol.state.last_accepted + step)
        if not assert_invariants(pol, name, 0, "fill", prev):
            ok = False

    for i, delta in enumerate(edges):
        prev = snapshot_accounting(pol)
        path_before = pol.state.total_path
        # Construct target carefully
        try:
            target = pol.state.last_accepted + delta
        except Exception as e:
            record_failure(name, i, prev, f"delta={delta}", snapshot_accounting(pol), "no exception", str(e))
            ok = False
            continue
        accepted, reason = pol.try_accept(target)
        # Invariant: never path > b_global
        if pol.state.total_path > pol.cfg.b_global:
            record_failure(
                name,
                i,
                prev,
                f"move(delta={delta})",
                snapshot_accounting(pol),
                f"path <= {pol.cfg.b_global}",
                f"path={pol.state.total_path}",
            )
            ok = False
        if accepted and path_before + abs(delta) > pol.cfg.b_global:
            record_failure(
                name,
                i,
                prev,
                f"move(delta={delta})",
                snapshot_accounting(pol),
                "must reject overshoot",
                "accepted overshoot",
            )
            ok = False
        if not accepted and pol.state.total_path != path_before:
            record_failure(
                name,
                i,
                prev,
                f"move(delta={delta})",
                snapshot_accounting(pol),
                "path unchanged on reject",
                f"path {path_before} -> {pol.state.total_path}",
            )
            ok = False
        if not assert_invariants(pol, name, i, f"delta={delta}", prev):
            ok = False

    # Dedicated: start fresh, attempt huge positive delta from 0
    pol2 = FormalPolicy(
        cfg(cum_disp_limit=INT32_MAX // 2, authority_delta=INT32_MAX // 2, b_global=B_GLOBAL),
        origin=0,
        last=0,
    )
    prev = snapshot_accounting(pol2)
    accepted, reason = pol2.try_accept(INT32_MAX // 4)
    if accepted and pol2.state.total_path > B_GLOBAL:
        record_failure(
            name, 100, prev, "huge_delta", snapshot_accounting(pol2), f"path<={B_GLOBAL}", f"path={pol2.state.total_path}"
        )
        ok = False
    if not assert_invariants(pol2, name, 100, "huge_delta", prev):
        ok = False

    RESULTS["matrix"][name] = {"pass": ok, "edges_tested": edges}
    return ok


def run_origin_and_path_combination() -> bool:
    name = "ORIGIN_AND_PATH_COMBINATION"
    pol = FormalPolicy(cfg(allow_full_reset=True, full_reset_clears_path=False), origin=0, last=0)
    ok = True
    ops = []
    # scripted interleave
    for round_i in range(100):
        ops.append(("move", 1))
        ops.append(("origin",))
        ops.append(("move_over",))  # will reject near end
        ops.append(("reauth",))
        if round_i % 20 == 19:
            ops.append(("recover",))

    for i, op in enumerate(ops):
        prev = snapshot_accounting(pol)
        if op[0] == "move":
            if abs(pol.state.last_accepted + 1 - pol.state.origin) > CUM:
                pol.set_authorized(True)
                pol.update_origin(None)
                pol.set_authorized(False)
            pol.try_accept(pol.state.last_accepted + 1)
        elif op[0] == "origin":
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
        elif op[0] == "move_over":
            # attempt large move
            pol.try_accept(pol.state.last_accepted + AUTH)
        elif op[0] == "reauth":
            pol.set_authorized(True)
            pol.set_authorized(False)
        elif op[0] == "recover":
            pol.full_reset(0)
        if not assert_invariants(pol, name, i, str(op), prev):
            ok = False

    RESULTS["matrix"][name] = {
        "pass": ok,
        "final_path": pol.state.total_path,
        "ops": len(ops),
    }
    return ok


def run_randomized_sequence() -> bool:
    name = "RANDOMIZED_SEQUENCE"
    rng = random.Random(SEED)
    pol = FormalPolicy(cfg(allow_full_reset=True, full_reset_clears_path=False), origin=0, last=0)
    ok = True
    N = 10_000

    for i in range(N):
        prev = snapshot_accounting(pol)
        choice = rng.randrange(6)
        if choice == 0:
            # valid small move
            delta = rng.choice([-1, 1, 2, -2, AUTH - 1, -(AUTH - 1)])
            if abs(delta) > AUTH:
                delta = 1 if delta > 0 else -1
            if abs(pol.state.last_accepted + delta - pol.state.origin) > CUM:
                pol.set_authorized(True)
                pol.update_origin(None)
                pol.set_authorized(False)
            pol.try_accept(pol.state.last_accepted + delta)
            op = f"move({delta})"
        elif choice == 1:
            # over-budget style move
            rem = B_GLOBAL - pol.state.total_path
            delta = rem + rng.randint(1, 5)
            if delta > AUTH:
                delta = AUTH
            if abs(pol.state.last_accepted + delta - pol.state.origin) > CUM:
                pol.set_authorized(True)
                pol.update_origin(None)
                pol.set_authorized(False)
            pol.try_accept(pol.state.last_accepted + delta)
            op = f"over_move({delta})"
        elif choice == 2:
            pol.set_authorized(True)
            pol.update_origin(None)
            op = "origin_auth"
        elif choice == 3:
            pol.set_authorized(False)
            pol.update_origin(None)
            op = "origin_unauth"
        elif choice == 4:
            pol.set_authorized(True)
            pol.set_authorized(False)
            op = "reauth"
        else:
            pol.full_reset(0)
            op = "recover"

        # remaining_budget invariant
        remaining = pol.cfg.b_global - pol.state.total_path
        if remaining != pol.cfg.b_global - pol.state.total_path:
            ok = False
        if pol.state.total_path > pol.cfg.b_global:
            record_failure(
                name, i, prev, op, snapshot_accounting(pol), f"path<={B_GLOBAL}", f"path={pol.state.total_path}"
            )
            ok = False
        if not assert_invariants(pol, name, i, op, prev):
            ok = False

    RESULTS["matrix"][name] = {
        "pass": ok,
        "operations": N,
        "final_path": pol.state.total_path,
        "seed": SEED,
    }
    return ok


def run_state_consistency() -> bool:
    name = "STATE_CONSISTENCY"
    pol = FormalPolicy(cfg(), origin=0, last=0)
    ok = True
    # Fill near budget
    while B_GLOBAL - pol.state.total_path > 5:
        if abs(pol.state.last_accepted + 1 - pol.state.origin) > CUM:
            pol.set_authorized(True)
            pol.update_origin(None)
            pol.set_authorized(False)
        pol.try_accept(pol.state.last_accepted + 1)

    for i in range(100):
        # deep copy relevant accounting fields before reject
        before = {
            "total_path": pol.state.total_path,
            "origin": pol.state.origin,
            "last_accepted": pol.state.last_accepted,
            "events_accepted": pol.state.events_accepted,
            "origin_updates": pol.state.origin_updates,
        }
        prev = snapshot_accounting(pol)
        accepted, reason = pol.try_accept(pol.state.last_accepted + AUTH)  # likely b_global or authority
        if accepted:
            # might accept if room — force reject by overshoot
            continue
        # accounting core must be unchanged
        if (
            pol.state.total_path != before["total_path"]
            or pol.state.origin != before["origin"]
            or pol.state.last_accepted != before["last_accepted"]
            or pol.state.events_accepted != before["events_accepted"]
            or pol.state.origin_updates != before["origin_updates"]
        ):
            record_failure(
                name,
                i,
                prev,
                "rejected_move",
                snapshot_accounting(pol),
                f"unchanged {before}",
                str(snapshot_accounting(pol)),
            )
            ok = False
        if not assert_invariants(pol, name, i, "reject", prev):
            ok = False

    RESULTS["matrix"][name] = {"pass": ok}
    return ok


def main() -> int:
    print(f"=== PHASE 15 Adversarial Budget Invariants  B_global={B_GLOBAL} ===\n")
    tests = [
        ("EXACT_BOUNDARY", run_exact_boundary),
        ("OVERSHOOT", run_overshoot),
        ("REJECTED_MOVE_ACCOUNTING", run_rejected_move_accounting),
        ("ORIGIN_UPDATE_LOOP", run_origin_update_loop),
        ("REAUTH_LOOP", run_reauth_loop),
        ("RECOVERY_LOOP", run_recovery_loop),
        ("INTEGER_EDGE_VALUES", run_integer_edge_values),
        ("ORIGIN_AND_PATH_COMBINATION", run_origin_and_path_combination),
        ("RANDOMIZED_SEQUENCE", run_randomized_sequence),
        ("STATE_CONSISTENCY", run_state_consistency),
    ]

    all_pass = True
    for label, fn in tests:
        print(f"Running {label}...", flush=True)
        try:
            passed = fn()
        except Exception as e:
            passed = False
            RESULTS["matrix"][label] = {"pass": False, "error": str(e)}
            record_failure(label, -1, {}, "exception", {}, "no exception", str(e))
            print(f"  ERROR: {e}")
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}")

    RESULTS["all_pass"] = all_pass
    RESULTS["failure_count"] = len(FAILURES)

    print("\n=== PASS/FAIL MATRIX ===")
    for label, _ in tests:
        m = RESULTS["matrix"].get(label, {})
        print(f"  {'PASS' if m.get('pass') else 'FAIL'}: {label}")
    print(f"\nALL_PASS={all_pass}  failures_recorded={len(FAILURES)}")

    out = "/home/workdir/artifacts/phase15/PHASE_15_RESULTS.json"
    with open(out, "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"Results → {out}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
