#!/usr/bin/env python3
"""Formal experimental policy layer + non-replenishable B_global (Phase 14).

RECONSTRUCTED research harness. Production PPM-Edge kernel is never modified.

Adds a global path budget that is NOT reset by origin updates, session-style
re-auth, or spatial envelope replenishment.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple, Dict, Any
import hashlib
import json


@dataclass
class PolicyConfig:
    authority_delta: int
    cum_disp_limit: int
    b_global: int = 100_000          # non-replenishable Σ|Δ| cap; use a large int as "∞"
    origin_update_requires_auth: bool = True
    origin_update_cost: int = 0      # optional charge against path on origin update
    allow_origin_reset_to_current: bool = True
    allow_full_reset: bool = False
    # If True, full_reset also clears total_path (should stay False for non-replenishable)
    full_reset_clears_path: bool = False


@dataclass
class PolicyState:
    origin: int = 0
    last_accepted: int = 0
    events_accepted: int = 0
    events_rejected: int = 0
    origin_updates: int = 0
    total_path: int = 0
    max_excursion: int = 0
    block_reasons: Dict[str, int] = field(default_factory=dict)
    history_deltas: List[int] = field(default_factory=list)
    transition_log: List[str] = field(default_factory=list)


class FormalPolicy:
    """
    Allowed trajectory under config C:
      1. |v_i - v_{i-1}| <= C.authority_delta
      2. |v_i - origin_i| <= C.cum_disp_limit
      3. total_path + |Δ| <= C.b_global          (NEW, non-replenishable)
    Origin updates do not decrease total_path.
    """

    def __init__(self, config: PolicyConfig, origin: int = 0, last: int = 0):
        self.cfg = config
        self.state = PolicyState(origin=origin, last_accepted=last)
        self.initial_origin = origin
        self._authorized = True

    def is_allowed(self, value: int, last: Optional[int] = None) -> Tuple[bool, str]:
        last = self.state.last_accepted if last is None else last
        d = abs(value - last)
        if d > self.cfg.authority_delta:
            return False, "authority"
        if abs(value - self.state.origin) > self.cfg.cum_disp_limit:
            return False, "cum_disp"
        if self.state.total_path + d > self.cfg.b_global:
            return False, "b_global"
        return True, "pass"

    def try_accept(self, value: int) -> Tuple[bool, str]:
        ok, reason = self.is_allowed(value)
        if not ok:
            self.state.events_rejected += 1
            self.state.block_reasons[reason] = self.state.block_reasons.get(reason, 0) + 1
            self.state.transition_log.append(f"REJECT:{reason}")
            return False, reason
        d = abs(value - self.state.last_accepted)
        self.state.total_path += d
        self.state.last_accepted = value
        self.state.events_accepted += 1
        self.state.max_excursion = max(
            self.state.max_excursion,
            abs(value - self.initial_origin),
        )
        self.state.history_deltas.append(d)
        self.state.transition_log.append("ACCEPT")
        return True, "pass"

    def update_origin(self, new_origin: Optional[int] = None, force: bool = False) -> Tuple[bool, str]:
        if self.cfg.origin_update_requires_auth and not (self._authorized or force):
            self.state.transition_log.append("ORIGIN_DENIED")
            return False, "origin_denied"
        if new_origin is None:
            if not self.cfg.allow_origin_reset_to_current:
                return False, "origin_reset_disabled"
            new_origin = self.state.last_accepted
        # Optional path charge for origin update (does not replenish path)
        cost = self.cfg.origin_update_cost
        if cost > 0:
            if self.state.total_path + cost > self.cfg.b_global:
                self.state.events_rejected += 1
                self.state.block_reasons["b_global"] = self.state.block_reasons.get("b_global", 0) + 1
                self.state.transition_log.append("REJECT:b_global:origin_cost")
                return False, "b_global"
            self.state.total_path += cost
        self.state.origin = new_origin
        self.state.origin_updates += 1
        self.state.transition_log.append(f"ORIGIN->{new_origin}")
        return True, "origin_updated"

    def set_authorized(self, flag: bool) -> None:
        self._authorized = flag
        self.state.transition_log.append(f"AUTH_TOKEN={flag}")

    def full_reset(self, baseline: int = 0) -> Tuple[bool, str]:
        if not self.cfg.allow_full_reset:
            return False, "full_reset_disabled"
        saved_path = self.state.total_path
        self.state = PolicyState(origin=baseline, last_accepted=baseline)
        if not self.cfg.full_reset_clears_path:
            self.state.total_path = saved_path  # non-replenishable
        self.initial_origin = baseline
        self.state.transition_log.append("FULL_RESET")
        return True, "reset"

    def snapshot(self) -> Dict[str, Any]:
        return {
            "config": asdict(self.cfg),
            "state": {
                "origin": self.state.origin,
                "last_accepted": self.state.last_accepted,
                "events_accepted": self.state.events_accepted,
                "events_rejected": self.state.events_rejected,
                "origin_updates": self.state.origin_updates,
                "total_path": self.state.total_path,
                "max_excursion": self.state.max_excursion,
                "block_reasons": dict(self.state.block_reasons),
            },
            "initial_origin": self.initial_origin,
            "authorized": self._authorized,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
