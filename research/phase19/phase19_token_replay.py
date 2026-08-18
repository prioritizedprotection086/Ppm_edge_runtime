#!/usr/bin/env python3
"""Phase 19 — Auth token replay, double-spend, privilege window (harness-only).

Not a claim against production C kernel.
"""
from __future__ import annotations

import json
import random
import sys
from typing import Any, Dict, List

from token_policy import TokenConfig, TokenPolicy

B_GLOBAL = 50_000
SEED = 19
FAILURES: List[Dict[str, Any]] = []
MATRIX: Dict[str, Any] = {}
RESULTS: Dict[str, Any] = {
    "phase": 19,
    "label": "harness-level only — not a claim against production C kernel",
    "config": {"b_global": B_GLOBAL, "seed": SEED, "max_updates_per_epoch": 3},
    "matrix": MATRIX,
    "failures": FAILURES,
}


def snap(p: TokenPolicy) -> Dict[str, Any]:
    return p.snapshot()


def unchanged(a: Dict[str, Any], b: Dict[str, Any], keys=None) -> bool:
    keys = keys or (
        "path_sum",
        "origin_budget",
        "session_id",
        "epoch",
        "updates_this_epoch",
        "origin",
        "value",
        "origin_updates",
        "used_tokens",
        "issued_count",
    )
    return all(a.get(k) == b.get(k) for k in keys)


def fail(test: str, msg: str, before=None, after=None) -> None:
    FAILURES.append({"test": test, "msg": msg, "before": before, "after": after})


def test_token_issue_and_use() -> bool:
    name = "TOKEN_ISSUE_AND_USE"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL))
    tok = p.issue_token()
    before = snap(p)
    ok, reason = p.update_origin(tok)
    after = snap(p)
    passed = ok and reason == "origin_updated" and after["origin_budget"] == before["origin_budget"] - 1
    passed = passed and tok in after["used_tokens"]
    if not passed:
        fail(name, f"ok={ok} reason={reason}", before, after)
    MATRIX[name] = {"pass": passed}
    return passed


def test_token_replay() -> bool:
    name = "TOKEN_REPLAY"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL))
    tok = p.issue_token()
    p.update_origin(tok)
    before = snap(p)
    ok, reason = p.update_origin(tok)
    after = snap(p)
    passed = (not ok) and reason == "token_replay" and unchanged(before, after)
    if not passed:
        fail(name, f"ok={ok} reason={reason}", before, after)
    # Replay 50 more times
    for i in range(50):
        b = snap(p)
        ok, reason = p.update_origin(tok)
        a = snap(p)
        if ok or reason != "token_replay" or not unchanged(b, a):
            fail(name, f"replay {i}: ok={ok} reason={reason}", b, a)
            passed = False
            break
    MATRIX[name] = {"pass": passed}
    return passed


def test_unknown_forged_token() -> bool:
    name = "UNKNOWN_FORGED_TOKEN"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL))
    p.issue_token()
    before = snap(p)
    ok = True
    for tok in (None, "", "deadbeef", "a" * 24, 123, 1.5, [], {}):
        b = snap(p)
        accepted, reason = p.update_origin(tok if isinstance(tok, str) or tok is None else str(tok))
        # non-str handled as missing/unknown
        a = snap(p)
        if accepted or not unchanged(b, a):
            fail(name, f"tok={tok!r} accepted={accepted} reason={reason}", b, a)
            ok = False
    # forged string not in issued set
    b = snap(p)
    accepted, reason = p.update_origin("0" * 24)
    a = snap(p)
    if accepted or reason != "token_unknown" or not unchanged(b, a):
        fail(name, f"forged accepted={accepted} reason={reason}", b, a)
        ok = False
    MATRIX[name] = {"pass": ok}
    return ok


def test_double_spend_two_ops() -> bool:
    name = "DOUBLE_SPEND"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL))
    tok = p.issue_token()
    ok1, _ = p.update_origin(tok, new_origin=10)
    before = snap(p)
    ok2, reason = p.update_origin(tok, new_origin=20)
    after = snap(p)
    passed = ok1 and (not ok2) and reason == "token_replay" and after["origin"] == 10
    passed = passed and unchanged(before, after)
    if not passed:
        fail(name, f"ok1={ok1} ok2={ok2} reason={reason}", before, after)
    MATRIX[name] = {"pass": passed}
    return passed


def test_epoch_limit() -> bool:
    name = "EPOCH_LIMIT"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL, max_updates_per_epoch=3))
    toks = [p.issue_token() for _ in range(5)]
    results = []
    for t in toks:
        results.append(p.update_origin(t))
    # First 3 succeed, next hit epoch_limit (budget still remains)
    passed = all(r[0] for r in results[:3]) and not results[3][0] and results[3][1] == "epoch_limit"
    # toks[3] was rejected with epoch_limit → token NOT consumed
    # After reauth, epoch opens: toks[3] should succeed once
    p.reauth()
    ok, reason = p.update_origin(toks[3])
    if not ok:
        passed = False
        fail(name, f"unused token after reauth should work: {reason}")
    # Replay toks[3] now must fail
    ok, reason = p.update_origin(toks[3])
    if ok or reason != "token_replay":
        passed = False
        fail(name, f"replay after reauth: {reason}")
    # Previously successful toks[0] still replay-blocked
    ok, reason = p.update_origin(toks[0])
    if ok or reason != "token_replay":
        passed = False
        fail(name, f"old used token after reauth: {reason}")
    fresh = p.issue_token()
    ok, reason = p.update_origin(fresh)
    if not ok:
        passed = False
        fail(name, f"fresh after reauth failed: {reason}")
    # path_sum / origin_budget must not increase on reauth
    # origin_budget decreased by successful updates only
    MATRIX[name] = {"pass": passed, "updates": p.state.origin_updates, "epoch": p.state.epoch}
    return passed


def test_reauth_no_replenish() -> bool:
    name = "REAUTH_NO_REPLENISH"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL))
    for _ in range(100):
        p.try_move(1)
        if abs(p.state.value - p.state.origin) > 400:
            t = p.issue_token()
            p.update_origin(t)
    path_before = p.state.path_sum
    ob_before = p.state.origin_budget
    p.reauth()
    passed = p.state.path_sum == path_before and p.state.origin_budget == ob_before
    if not passed:
        fail(name, f"path {path_before}->{p.state.path_sum} ob {ob_before}->{p.state.origin_budget}")
    MATRIX[name] = {"pass": passed}
    return passed


def test_rejected_no_consume() -> bool:
    name = "REJECTED_NO_CONSUME"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL))
    tok = p.issue_token()
    before = snap(p)
    # Fail epoch by using up epoch with other tokens first
    for _ in range(3):
        p.update_origin(p.issue_token())
    # Now tok still unused — but epoch limit
    b = snap(p)
    ok, reason = p.update_origin(tok)
    a = snap(p)
    passed = (not ok) and reason == "epoch_limit"
    # Token must NOT be marked used
    passed = passed and tok not in p.state.used_tokens
    # origin_budget unchanged by rejected attempt
    passed = passed and a["origin_budget"] == b["origin_budget"]
    if not passed:
        fail(name, f"ok={ok} reason={reason} used={tok in p.state.used_tokens}", b, a)
    MATRIX[name] = {"pass": passed}
    return passed


def test_budget_exhausted() -> bool:
    name = "BUDGET_EXHAUSTED"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL, initial_origin_budget=2, max_updates_per_epoch=100))
    t1, t2, t3 = p.issue_token(), p.issue_token(), p.issue_token()
    p.update_origin(t1)
    p.update_origin(t2)
    before = snap(p)
    ok, reason = p.update_origin(t3)
    after = snap(p)
    passed = (not ok) and reason == "origin_budget_exhausted" and unchanged(before, after)
    passed = passed and t3 not in p.state.used_tokens
    if not passed:
        fail(name, f"ok={ok} reason={reason}", before, after)
    MATRIX[name] = {"pass": passed}
    return passed


def test_path_invariants_with_tokens() -> bool:
    name = "PATH_INVARIANTS"
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL))
    ok = True
    for i in range(1000):
        before = p.state.path_sum
        p.try_move(1 if i % 2 == 0 else -1)
        if abs(p.state.value - p.state.origin) >= p.cfg.cum_disp_limit - 1:
            t = p.issue_token()
            p.update_origin(t)
            if p.state.updates_this_epoch >= p.cfg.max_updates_per_epoch:
                p.reauth()
        if p.state.path_sum < before:
            fail(name, f"path decreased {before}->{p.state.path_sum}")
            ok = False
            break
        if p.state.path_sum > B_GLOBAL:
            fail(name, f"path > B_global: {p.state.path_sum}")
            ok = False
            break
    MATRIX[name] = {"pass": ok, "final_path": p.state.path_sum}
    return ok


def test_randomized() -> bool:
    name = "RANDOMIZED_TOKEN_OPS"
    rng = random.Random(SEED)
    p = TokenPolicy(TokenConfig(b_global=B_GLOBAL, max_updates_per_epoch=3))
    tokens: List[str] = []
    ok = True
    N = 10_000
    for i in range(N):
        before = snap(p)
        choice = rng.randrange(7)
        if choice == 0:
            tokens.append(p.issue_token())
        elif choice == 1:
            t = tokens[rng.randrange(len(tokens))] if tokens else "noused"
            p.update_origin(t)
        elif choice == 2:
            p.update_origin("forged" + str(rng.randrange(1000)))
        elif choice == 3:
            p.try_move(rng.choice([-2, -1, 1, 2]))
        elif choice == 4:
            p.reauth()
        elif choice == 5:
            if tokens:
                p.update_origin(tokens[0])  # likely replay
        else:
            p.update_origin(None)

        after = snap(p)
        if after["path_sum"] < before["path_sum"]:
            fail(name, f"path dec at {i}", before, after)
            ok = False
            break
        if after["path_sum"] > B_GLOBAL:
            fail(name, f"path oob at {i}", before, after)
            ok = False
            break
        if after["origin_budget"] > before["origin_budget"]:
            # only issue_budget can increase — we never call it here
            fail(name, f"ob increased at {i}", before, after)
            ok = False
            break
        if after["epoch"] < before["epoch"]:
            fail(name, f"epoch backward at {i}", before, after)
            ok = False
            break

    MATRIX[name] = {"pass": ok, "operations": N, "seed": SEED}
    return ok


def main() -> int:
    print(f"=== PHASE 19 Token Replay / Capability (harness-only) B_global={B_GLOBAL} ===\n")
    print("NOTE: Harness-level only. Not a claim against production C kernel.\n")

    tests = [
        ("TOKEN_ISSUE_AND_USE", test_token_issue_and_use),
        ("TOKEN_REPLAY", test_token_replay),
        ("UNKNOWN_FORGED_TOKEN", test_unknown_forged_token),
        ("DOUBLE_SPEND", test_double_spend_two_ops),
        ("EPOCH_LIMIT", test_epoch_limit),
        ("REAUTH_NO_REPLENISH", test_reauth_no_replenish),
        ("REJECTED_NO_CONSUME", test_rejected_no_consume),
        ("BUDGET_EXHAUSTED", test_budget_exhausted),
        ("PATH_INVARIANTS", test_path_invariants_with_tokens),
        ("RANDOMIZED_TOKEN_OPS", test_randomized),
    ]

    all_pass = True
    for label, fn in tests:
        print(f"Running {label}...", flush=True)
        try:
            passed = fn()
        except Exception as e:
            passed = False
            MATRIX[label] = {"pass": False, "error": str(e)}
            fail(label, str(e))
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

    out = "/home/workdir/artifacts/phase19/PHASE_19_RESULTS.json"
    with open(out, "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"Results → {out}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
