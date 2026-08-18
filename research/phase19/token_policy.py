#!/usr/bin/env python3
"""Phase 19 capability model (RECONSTRUCTED harness).

One-time auth tokens for origin updates + privilege windows.
Production PPM-Edge kernel is NEVER modified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set, Tuple
import hashlib
import secrets


@dataclass
class TokenConfig:
    authority_delta: int = 20
    cum_disp_limit: int = 500
    b_global: int = 50_000
    initial_origin_budget: int = 10
    # Privilege window: max origin updates per reauth epoch (in addition to tokens)
    max_updates_per_epoch: int = 3


@dataclass
class TokenState:
    origin: int = 0
    value: int = 0
    path_sum: int = 0
    origin_budget: int = 10
    session_id: int = 1
    epoch: int = 1
    updates_this_epoch: int = 0
    events_accepted: int = 0
    events_rejected: int = 0
    origin_updates: int = 0
    block_reasons: Dict[str, int] = field(default_factory=dict)
    used_tokens: Set[str] = field(default_factory=set)
    issued_tokens: Set[str] = field(default_factory=set)


class TokenPolicy:
    """
    Invariants:
      1. 0 <= path_sum <= b_global; path_sum never decreases
      2. Each origin-update token is single-use
      3. Replay of a used token is rejected; state unchanged
      4. Unknown / forged tokens rejected
      5. origin_budget never increases except via explicit issue_budget (admin)
      6. updates_this_epoch cannot exceed max_updates_per_epoch without new epoch
      7. reauth advances epoch and resets updates_this_epoch but NOT path_sum/origin_budget
      8. Rejected ops do not consume tokens or budget
    """

    def __init__(self, config: Optional[TokenConfig] = None):
        self.cfg = config or TokenConfig()
        self.state = TokenState(origin_budget=self.cfg.initial_origin_budget)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "path_sum": self.state.path_sum,
            "origin_budget": self.state.origin_budget,
            "session_id": self.state.session_id,
            "epoch": self.state.epoch,
            "updates_this_epoch": self.state.updates_this_epoch,
            "origin": self.state.origin,
            "value": self.state.value,
            "origin_updates": self.state.origin_updates,
            "used_tokens": sorted(self.state.used_tokens),
            "issued_count": len(self.state.issued_tokens),
        }

    def issue_token(self) -> str:
        """Issue a fresh one-time origin-update token."""
        tok = hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:24]
        self.state.issued_tokens.add(tok)
        return tok

    def try_move(self, delta: int) -> Tuple[bool, str]:
        if abs(delta) > self.cfg.authority_delta:
            self.state.events_rejected += 1
            self.state.block_reasons["authority"] = self.state.block_reasons.get("authority", 0) + 1
            return False, "authority"
        new_value = self.state.value + delta
        if abs(new_value - self.state.origin) > self.cfg.cum_disp_limit:
            self.state.events_rejected += 1
            self.state.block_reasons["cum_disp"] = self.state.block_reasons.get("cum_disp", 0) + 1
            return False, "cum_disp"
        cost = abs(delta)
        if self.state.path_sum + cost > self.cfg.b_global:
            self.state.events_rejected += 1
            self.state.block_reasons["b_global"] = self.state.block_reasons.get("b_global", 0) + 1
            return False, "b_global"
        self.state.path_sum += cost
        self.state.value = new_value
        self.state.events_accepted += 1
        return True, "pass"

    def update_origin(self, token: Optional[str], new_origin: Optional[int] = None) -> Tuple[bool, str]:
        """Origin update requires a valid, unused, issued token."""
        st = self.state

        def reject(reason: str) -> Tuple[bool, str]:
            st.events_rejected += 1
            st.block_reasons[reason] = st.block_reasons.get(reason, 0) + 1
            return False, reason

        if token is None or not isinstance(token, str):
            return reject("token_missing")
        if token not in st.issued_tokens:
            return reject("token_unknown")
        if token in st.used_tokens:
            return reject("token_replay")
        if st.origin_budget <= 0:
            return reject("origin_budget_exhausted")
        if st.updates_this_epoch >= self.cfg.max_updates_per_epoch:
            return reject("epoch_limit")

        # All checks passed — consume token and budget
        st.used_tokens.add(token)
        st.origin_budget -= 1
        st.updates_this_epoch += 1
        st.origin_updates += 1
        if new_origin is None:
            new_origin = st.value
        st.origin = int(new_origin)
        return True, "origin_updated"

    def reauth(self) -> None:
        """New privilege epoch: reset epoch counter only — not path or origin_budget."""
        self.state.epoch += 1
        self.state.updates_this_epoch = 0
        self.state.session_id += 1

    def issue_budget(self, n: int) -> Tuple[bool, str]:
        """Admin-only style grant (for tests). Not available via token."""
        if n < 0:
            return False, "bad_grant"
        self.state.origin_budget += n
        return True, "granted"
