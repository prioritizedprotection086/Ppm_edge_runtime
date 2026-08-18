#!/usr/bin/env python3
"""
PPM-Edge Experimental Harness (Phase 12)
========================================
Minimal non-production testbed to prove or disprove the existence of a
non-replenishable global path budget B_global.

Production kernel is NEVER touched.
All arithmetic uses integers only.
"""

from __future__ import annotations
import argparse
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Set, Dict, Any
from enum import Enum, auto


class Decision(Enum):
    ACCEPT = auto()
    REJECT_SPATIAL = auto()
    REJECT_PATH = auto()
    REJECT_ORIGIN_BUDGET = auto()
    REJECT_TOKEN = auto()


@dataclass
class EventResult:
    event_type: str
    delta: Optional[int]
    decision: str
    value_after: int
    origin_after: int
    path_sum_after: int
    origin_budget_after: int


@dataclass
class HarnessConfig:
    B_global: int = 1_000_000          # set to a very large number to simulate "unbounded"
    cum_disp_limit: int = 500
    authority_delta: int = 20
    origin_budget: int = 5             # finite origin-update budget
    initial_value: int = 0
    initial_origin: int = 0
    allow_origin_updates: bool = True
    # If True, path_sum survives session/recovery/reauth (non-replenishable)
    path_budget_survives_reset: bool = True


@dataclass
class HarnessState:
    value: int = 0
    origin: int = 0
    path_sum: int = 0
    origin_budget: int = 0
    used_tokens: Set[str] = field(default_factory=set)
    session_id: int = 0
    event_log: List[EventResult] = field(default_factory=list)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "origin": self.origin,
            "path_sum": self.path_sum,
            "origin_budget": self.origin_budget,
            "session_id": self.session_id,
            "used_tokens_count": len(self.used_tokens),
        }


class PPMEdgeHarness:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.state = HarnessState(
            value=config.initial_value,
            origin=config.initial_origin,
            origin_budget=config.origin_budget if config.allow_origin_updates else 0,
        )
        self._token_counter = 0

    def _log(self, event_type: str, delta: Optional[int], decision: Decision):
        self.state.event_log.append(
            EventResult(
                event_type=event_type,
                delta=delta,
                decision=decision.name,
                value_after=self.state.value,
                origin_after=self.state.origin,
                path_sum_after=self.state.path_sum,
                origin_budget_after=self.state.origin_budget,
            )
        )

    def move(self, delta: int) -> Decision:
        """Apply a movement Δ under spatial + path budgets."""
        new_value = self.state.value + delta
        # Spatial check
        if abs(new_value - self.state.origin) > self.config.cum_disp_limit:
            self._log("move", delta, Decision.REJECT_SPATIAL)
            return Decision.REJECT_SPATIAL
        # Path budget check
        if self.state.path_sum + abs(delta) > self.config.B_global:
            self._log("move", delta, Decision.REJECT_PATH)
            return Decision.REJECT_PATH
        # Accept
        self.state.value = new_value
        self.state.path_sum += abs(delta)
        self._log("move", delta, Decision.ACCEPT)
        return Decision.ACCEPT

    def request_origin_token(self) -> Optional[str]:
        """Mint a one-time origin-update token (simulates authorization)."""
        if not self.config.allow_origin_updates:
            return None
        self._token_counter += 1
        token = f"tok-{self._token_counter}-{int(time.time()*1000)}"
        return token

    def origin_update(self, token: str, new_origin: int) -> Decision:
        """Attempt an origin update with a one-time token."""
        if not self.config.allow_origin_updates:
            self._log("origin_update", None, Decision.REJECT_ORIGIN_BUDGET)
            return Decision.REJECT_ORIGIN_BUDGET
        if token in self.state.used_tokens:
            self._log("origin_update", None, Decision.REJECT_TOKEN)
            return Decision.REJECT_TOKEN
        if self.state.origin_budget <= 0:
            self._log("origin_update", None, Decision.REJECT_ORIGIN_BUDGET)
            return Decision.REJECT_ORIGIN_BUDGET
        # Accept
        self.state.origin = new_origin
        self.state.origin_budget -= 1
        self.state.used_tokens.add(token)
        self._log("origin_update", None, Decision.ACCEPT)
        return Decision.ACCEPT

    def simulate_session_restart(self):
        """Simulate a new session. Path budget survival is configurable."""
        self.state.session_id += 1
        if not self.config.path_budget_survives_reset:
            self.state.path_sum = 0  # replenishable case (bad)
        # origin_budget and used_tokens intentionally kept to test non-replenishable origin capability

    def simulate_recovery(self, checkpoint: Dict[str, Any]):
        """Restore a checkpoint. Tests whether path_sum is restored correctly."""
        self.state.value = checkpoint["value"]
        self.state.origin = checkpoint["origin"]
        self.state.path_sum = checkpoint["path_sum"]  # correct restore keeps the budget
        self.state.origin_budget = checkpoint["origin_budget"]
        self.state.session_id = checkpoint["session_id"]

    def simulate_reauth(self):
        """Simulate higher-privilege re-authentication. Path budget must survive."""
        # Intentionally does nothing to path_sum or origin_budget
        pass

    def run_oscillation(self, max_events: int = 100_000, amplitude: Optional[int] = None) -> int:
        """Drive ±amplitude until rejection or max_events. Returns accepted count."""
        if amplitude is None:
            amplitude = self.config.authority_delta - 1
        accepted = 0
        direction = 1
        for _ in range(max_events):
            delta = direction * amplitude
            decision = self.move(delta)
            if decision == Decision.ACCEPT:
                accepted += 1
                # bounce if we are near the spatial edge to stay inside envelope longer
                if abs(self.state.value + delta - self.state.origin) > self.config.cum_disp_limit - amplitude:
                    direction *= -1
            else:
                break
        return accepted

    def summary(self) -> Dict[str, Any]:
        return {
            "config": asdict(self.config),
            "final_state": self.state.snapshot(),
            "total_events": len(self.state.event_log),
            "accepted_moves": sum(1 for e in self.state.event_log if e.event_type == "move" and e.decision == "ACCEPT"),
            "rejected_path": sum(1 for e in self.state.event_log if e.decision == "REJECT_PATH"),
            "rejected_spatial": sum(1 for e in self.state.event_log if e.decision == "REJECT_SPATIAL"),
            "origin_updates_accepted": sum(1 for e in self.state.event_log if e.event_type == "origin_update" and e.decision == "ACCEPT"),
        }


def run_vector_A(verbose: bool = True) -> Dict[str, Any]:
    """Pure oscillation exhaustion."""
    cfg = HarnessConfig(B_global=1_000_000, origin_budget=0, allow_origin_updates=False)
    h = PPMEdgeHarness(cfg)
    accepted = h.run_oscillation()
    result = h.summary()
    result["vector"] = "A_pure_oscillation"
    result["accepted_count"] = accepted
    result["path_sum"] = h.state.path_sum
    result["hit_budget"] = h.state.path_sum >= cfg.B_global or result["rejected_path"] > 0
    if verbose:
        print(f"[A] accepted={accepted} path_sum={h.state.path_sum} hit_budget={result['hit_budget']}")
    return result


def run_vector_B(verbose: bool = True) -> Dict[str, Any]:
    """Session restart probe – budget should survive."""
    cfg = HarnessConfig(B_global=50_000, origin_budget=0, allow_origin_updates=False,
                        path_budget_survives_reset=True)
    h = PPMEdgeHarness(cfg)
    h.run_oscillation()
    path_before = h.state.path_sum
    h.simulate_session_restart()
    accepted_after = h.run_oscillation(max_events=1000)
    result = h.summary()
    result["vector"] = "B_session_restart"
    result["path_before_restart"] = path_before
    result["accepted_after_restart"] = accepted_after
    result["budget_survived"] = accepted_after == 0
    if verbose:
        print(f"[B] path_before={path_before} accepted_after={accepted_after} survived={result['budget_survived']}")
    return result


def run_vector_C(verbose: bool = True) -> Dict[str, Any]:
    """Recovery / checkpoint probe."""
    cfg = HarnessConfig(B_global=50_000, origin_budget=0, allow_origin_updates=False)
    h = PPMEdgeHarness(cfg)
    # Run part way
    h.run_oscillation(max_events=1000)
    checkpoint = h.state.snapshot()
    # Exhaust
    h.run_oscillation()
    path_exhausted = h.state.path_sum
    # Restore checkpoint (correct restore keeps high path_sum? Wait – we restore earlier lower path_sum)
    # For the test we restore the mid-point and then continue; if the budget is the remaining capacity it should still stop at B_global
    h.simulate_recovery(checkpoint)
    accepted_after = h.run_oscillation()
    result = h.summary()
    result["vector"] = "C_recovery"
    result["path_at_checkpoint"] = checkpoint["path_sum"]
    result["path_after_exhaust_before_restore"] = path_exhausted
    result["accepted_after_restore"] = accepted_after
    result["final_path"] = h.state.path_sum
    result["never_exceeded"] = h.state.path_sum <= cfg.B_global
    if verbose:
        print(f"[C] final_path={h.state.path_sum} never_exceeded={result['never_exceeded']}")
    return result


def run_vector_D(verbose: bool = True) -> Dict[str, Any]:
    """Re-auth probe – budget must survive."""
    cfg = HarnessConfig(B_global=30_000, origin_budget=0, allow_origin_updates=False)
    h = PPMEdgeHarness(cfg)
    h.run_oscillation()
    h.simulate_reauth()
    accepted_after = h.run_oscillation(max_events=500)
    result = h.summary()
    result["vector"] = "D_reauth"
    result["accepted_after_reauth"] = accepted_after
    result["budget_survived"] = accepted_after == 0
    if verbose:
        print(f"[D] accepted_after_reauth={accepted_after} survived={result['budget_survived']}")
    return result


def run_vector_E(verbose: bool = True) -> Dict[str, Any]:
    """Origin-update budget + replay protection."""
    cfg = HarnessConfig(B_global=10_000_000, origin_budget=5, allow_origin_updates=True)
    h = PPMEdgeHarness(cfg)
    tokens = []
    accepted = 0
    for i in range(10):
        tok = h.request_origin_token()
        tokens.append(tok)
        decision = h.origin_update(tok, new_origin=i * 100)
        if decision == Decision.ACCEPT:
            accepted += 1
    # Replay first token
    replay_decision = h.origin_update(tokens[0], new_origin=9999)
    result = h.summary()
    result["vector"] = "E_origin_budget"
    result["origin_updates_accepted"] = accepted
    result["replay_rejected"] = replay_decision == Decision.REJECT_TOKEN
    result["pass"] = (accepted == 5) and result["replay_rejected"]
    if verbose:
        print(f"[E] accepted_updates={accepted} replay_rejected={result['replay_rejected']} pass={result['pass']}")
    return result


def run_vector_F(verbose: bool = True) -> Dict[str, Any]:
    """Combined interleaving of origin updates and oscillation."""
    cfg = HarnessConfig(B_global=100_000, origin_budget=3, allow_origin_updates=True,
                        cum_disp_limit=500)
    h = PPMEdgeHarness(cfg)
    for i in range(3):
        tok = h.request_origin_token()
        h.origin_update(tok, new_origin=i * 200)
        h.run_oscillation(max_events=2000)
    result = h.summary()
    result["vector"] = "F_interleaved"
    result["final_path"] = h.state.path_sum
    result["origin_updates_used"] = 3 - h.state.origin_budget
    result["path_within_budget"] = h.state.path_sum <= cfg.B_global
    if verbose:
        print(f"[F] final_path={h.state.path_sum} origins_used={result['origin_updates_used']}")
    return result


def run_vector_G(verbose: bool = True) -> Dict[str, Any]:
    """Tiny-Δ flood – check for overflow / precision issues."""
    cfg = HarnessConfig(B_global=100_000, origin_budget=0, allow_origin_updates=False,
                        authority_delta=2)  # amplitude will be 1
    h = PPMEdgeHarness(cfg)
    accepted = h.run_oscillation(max_events=200_000, amplitude=1)
    result = h.summary()
    result["vector"] = "G_tiny_delta"
    result["accepted"] = accepted
    result["path_sum"] = h.state.path_sum
    result["exact"] = h.state.path_sum == accepted  # each |Δ|=1
    if verbose:
        print(f"[G] accepted={accepted} path_sum={h.state.path_sum} exact={result['exact']}")
    return result


def run_all_vectors() -> Dict[str, Any]:
    print("=" * 60)
    print("PPM-Edge Experimental Harness – Phase 12 Vectors A–G")
    print("=" * 60)
    results = {
        "A": run_vector_A(),
        "B": run_vector_B(),
        "C": run_vector_C(),
        "D": run_vector_D(),
        "E": run_vector_E(),
        "F": run_vector_F(),
        "G": run_vector_G(),
    }
    print("=" * 60)
    print("SUMMARY")
    for k, v in results.items():
        print(f"  {k}: {json.dumps({key: v[key] for key in v if key != 'config'}, default=str)[:120]}...")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PPM-Edge Experimental Harness")
    parser.add_argument("--vector", choices=list("ABCDEFG") + ["all"], default="all")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    if args.vector == "all":
        results = run_all_vectors()
    else:
        fn = {
            "A": run_vector_A,
            "B": run_vector_B,
            "C": run_vector_C,
            "D": run_vector_D,
            "E": run_vector_E,
            "F": run_vector_F,
            "G": run_vector_G,
        }[args.vector]
        results = {args.vector: fn()}

    if args.json:
        print(json.dumps(results, indent=2, default=str))
