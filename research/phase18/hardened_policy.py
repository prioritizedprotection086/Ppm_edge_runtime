#!/usr/bin/env python3
"""Phase 17-style hardened recovery model (RECONSTRUCTED harness).

Production PPM-Edge kernel is NEVER modified.
This is a research policy layer with checkpoint serialization, session binding,
non-replenishable B_global, and origin_budget.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Tuple
import copy
import hashlib
import json


@dataclass
class HardenedConfig:
    authority_delta: int = 20
    cum_disp_limit: int = 500
    b_global: int = 50_000
    initial_origin_budget: int = 10
    origin_update_requires_auth: bool = True


@dataclass
class HardenedState:
    origin: int = 0
    value: int = 0  # last accepted operational value
    path_sum: int = 0
    origin_budget: int = 10
    session_id: int = 1
    events_accepted: int = 0
    events_rejected: int = 0
    origin_updates: int = 0
    block_reasons: Dict[str, int] = field(default_factory=dict)


class HardenedPolicy:
    """
    Security invariants (must hold after every accepted transition):
      1. 0 <= path_sum <= b_global
      2. path_sum never decreases
      3. origin_budget never increases except via explicit authorized grant
         (recovery must not increase it)
      4. session_id never moves backward
      5. checkpoint from older security state cannot replenish consumed budget
      6. checkpoint from another session cannot be accepted as trusted
      7. invalid checkpoint rejected safely
      8. rejected checkpoint does not partially modify security state
    """

    CHECKPOINT_FIELDS = (
        "origin",
        "value",
        "path_sum",
        "origin_budget",
        "session_id",
        "events_accepted",
        "origin_updates",
        "mac",  # integrity tag over trusted fields
    )

    def __init__(self, config: Optional[HardenedConfig] = None):
        self.cfg = config or HardenedConfig()
        self.state = HardenedState(origin_budget=self.cfg.initial_origin_budget)
        self._authorized = False
        self._secret = b"harness-only-not-production-secret-v17"

    # ---- helpers ----
    def _mac(self, payload: Dict[str, Any]) -> str:
        # Simple keyed hash for harness integrity (not a claim about C kernel crypto)
        material = json.dumps(
            {k: payload[k] for k in ("origin", "value", "path_sum", "origin_budget", "session_id")
             if k in payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(self._secret + material).hexdigest()[:32]

    def snapshot_security(self) -> Dict[str, Any]:
        return {
            "path_sum": self.state.path_sum,
            "origin_budget": self.state.origin_budget,
            "session_id": self.state.session_id,
            "origin": self.state.origin,
            "value": self.state.value,
            "events_accepted": self.state.events_accepted,
            "origin_updates": self.state.origin_updates,
        }

    def _copy_state(self) -> HardenedState:
        return copy.deepcopy(self.state)

    def _restore_state(self, st: HardenedState) -> None:
        self.state = st

    # ---- movement ----
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

    def set_authorized(self, flag: bool) -> None:
        self._authorized = bool(flag)

    def update_origin(self, new_origin: Optional[int] = None) -> Tuple[bool, str]:
        if self.cfg.origin_update_requires_auth and not self._authorized:
            return False, "origin_denied"
        if self.state.origin_budget <= 0:
            return False, "origin_budget_exhausted"
        if new_origin is None:
            new_origin = self.state.value
        self.state.origin = int(new_origin)
        self.state.origin_budget -= 1
        self.state.origin_updates += 1
        return True, "origin_updated"

    def reauth(self) -> None:
        """Re-authentication must not replenish path_sum or origin_budget."""
        self._authorized = True
        # session_id advances to mark security epoch
        self.state.session_id += 1

    def advance_session(self) -> None:
        self.state.session_id += 1
        self._authorized = False

    # ---- checkpoint ----
    def create_checkpoint(self) -> Dict[str, Any]:
        payload = {
            "origin": self.state.origin,
            "value": self.state.value,
            "path_sum": self.state.path_sum,
            "origin_budget": self.state.origin_budget,
            "session_id": self.state.session_id,
            "events_accepted": self.state.events_accepted,
            "origin_updates": self.state.origin_updates,
        }
        payload["mac"] = self._mac(payload)
        return payload

    def recover_from_checkpoint(self, cp: Any) -> Tuple[bool, str]:
        """
        Hardened recovery rules:
        - Must be a dict with required fields and valid types
        - MAC must verify
        - session_id must equal current session (no cross-session, no downgrade)
        - path_sum must be >= current path_sum (cannot replenish by loading older)
          AND path_sum <= b_global and path_sum >= 0
        - origin_budget must be <= current origin_budget (cannot increase via recovery)
        - On any failure: state unchanged
        """
        saved = self._copy_state()

        def fail(reason: str) -> Tuple[bool, str]:
            self._restore_state(saved)
            self.state.events_rejected += 1
            self.state.block_reasons[reason] = self.state.block_reasons.get(reason, 0) + 1
            return False, reason

        if cp is None:
            return fail("cp_null")
        if not isinstance(cp, dict):
            return fail("cp_type")

        required = ("origin", "value", "path_sum", "origin_budget", "session_id", "mac")
        for k in required:
            if k not in cp:
                return fail("cp_missing_field")

        # Type checks for security-critical fields
        for k in ("origin", "value", "path_sum", "origin_budget", "session_id"):
            v = cp[k]
            if isinstance(v, bool) or not isinstance(v, int):
                return fail("cp_bad_type")

        if not isinstance(cp["mac"], str):
            return fail("cp_bad_mac_type")

        # MAC integrity
        expected_mac = self._mac(cp)
        if cp["mac"] != expected_mac:
            return fail("cp_mac_invalid")

        path = cp["path_sum"]
        ob = cp["origin_budget"]
        sid = cp["session_id"]

        if path < 0 or path > self.cfg.b_global:
            return fail("cp_path_oob")
        if path < self.state.path_sum:
            return fail("cp_path_replenish")
        if ob < 0:
            return fail("cp_origin_budget_neg")
        if ob > self.state.origin_budget:
            return fail("cp_origin_budget_increase")
        if sid != self.state.session_id:
            return fail("cp_session_mismatch")
        if sid < 0:
            return fail("cp_session_neg")

        # Apply only after all checks
        self.state.origin = cp["origin"]
        self.state.value = cp["value"]
        self.state.path_sum = path
        self.state.origin_budget = ob
        # session_id stays (already matched)
        if "events_accepted" in cp and isinstance(cp["events_accepted"], int) and not isinstance(cp["events_accepted"], bool):
            self.state.events_accepted = max(self.state.events_accepted, cp["events_accepted"])
        if "origin_updates" in cp and isinstance(cp["origin_updates"], int) and not isinstance(cp["origin_updates"], bool):
            self.state.origin_updates = max(self.state.origin_updates, cp["origin_updates"])
        return True, "recovered"
