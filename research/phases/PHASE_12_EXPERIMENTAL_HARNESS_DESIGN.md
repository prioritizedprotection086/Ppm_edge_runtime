# PHASE 12 — EXPERIMENTAL HARNESS DESIGN
## Minimal Non-Production Testbed to Prove or Disprove \( B_{\text{global}} \)
**Production Kernel: FROZEN**  
**Date:** 2026-08-16 / 2026-08-17

---

### Purpose
Create a minimal, isolated experimental harness that can answer one binary question with concrete numbers:

> Does a non-replenishable global path budget \( B_{\text{global}} \) exist and survive session restart, recovery, and authority change?

If the answer is no, we have a confirmed gap.  
If the answer is yes, we can measure the exact bound and false-rejection cost.

This harness must **not** modify or link against production PPM-Edge code.

---

### 12.1 Harness Requirements

| Requirement | Rationale |
|-------------|-----------|
| Isolated process / container | No risk to production |
| Exact same numeric types and Δ semantics as the real policy | Results transferable |
| Controllable origin-update interface | Can enable / disable / budget it |
| Explicit global path accumulator | Can be inspected and forced |
| Session / recovery / re-auth simulation hooks | Test survival of budget |
| Deterministic event log | Every accepted / rejected Δ recorded |
| Reproducible seed & configuration dump | Independent verification |

---

### 12.2 Core State Machine (Minimal)

```text
State:
  value            : numeric
  origin           : numeric
  cum_disp_limit   : numeric          # spatial envelope
  path_sum         : numeric          # Σ|Δ|
  B_global         : numeric | ∞      # the budget under test
  origin_budget    : integer | ∞      # remaining origin updates
  authority_delta  : numeric
  session_id       : opaque
  auth_token_set   : set of one-time tokens

On movement event Δ:
  if |value + Δ − origin| > cum_disp_limit:      REJECT (spatial)
  if path_sum + |Δ| > B_global:                 REJECT (path budget)
  else:
    value     ← value + Δ
    path_sum  ← path_sum + |Δ|
    ACCEPT

On origin_update(token, new_origin):
  if token not in auth_token_set or already used: REJECT
  if origin_budget == 0:                          REJECT
  origin        ← new_origin
  origin_budget ← origin_budget − 1
  mark token used
  ACCEPT
```

---

### 12.3 Test Vectors (Exact)

**Vector A – Pure Oscillation Exhaustion**
```
B_global        = 1_000_000
cum_disp_limit  = 500
authority_delta = 20
origin fixed
Δ = ±19 repeated
Expected: acceptance stops at or before path_sum == 1_000_000
```

**Vector B – Session Restart Probe**
```
Run Vector A to exhaustion
Simulate session restart (new session_id, same path_sum & B_global)
Resume ±19
Expected: still rejected if budget is non-replenishable
```

**Vector C – Recovery / Checkpoint Probe**
```
Run Vector A to exhaustion
Restore a checkpoint taken before exhaustion
Resume
Expected: if path_sum is restored correctly → still rejected
         if path_sum is reset → FAIL (replenishable)
```

**Vector D – Authority / Re-auth Probe**
```
Run Vector A to exhaustion
Simulate higher-privilege re-authentication
Resume
Expected: budget still enforced
```

**Vector E – Origin-Update Budget**
```
origin_budget = 5
Attempt 10 origin updates with fresh tokens
Expected: exactly 5 accepted, rest rejected
Replay any previous token → rejected
```

**Vector F – Combined Interleaving**
```
Mix origin updates and ±19 oscillation
Record final path_sum and origin updates consumed
Verify both budgets independently enforced
```

**Vector G – Tiny-Δ Flood (Overflow / Precision)**
```
Δ = ±1 (or smallest representable)
Run until near B_global
Verify no wrap-around or lost counts
```

---

### 12.4 Success / Failure Criteria

| Outcome | Meaning |
|---------|---------|
| All vectors pass | Strongest model is realizable and can be measured |
| Any vector shows budget reset | Confirmed gap — budget is replenishable under that condition |
| Path continues after B_global | No global path budget exists in the tested layer |
| Origin updates unlimited | Origin authority is unconstrained |

---

### 12.5 Deliverables from Running the Harness

1. Exact maximum path length achieved  
2. Exact number of origin updates accepted  
3. Pass/fail matrix for Vectors A–G  
4. Event trace (accepted / rejected) for the critical failure case  
5. Configuration dump + source hash of the harness itself  

---

### 12.6 Implementation Notes

- Language: any memory-safe language with exact integer or fixed-point arithmetic (Rust, Python with decimal, etc.).
- No floating-point for the path accumulator.
- All configuration values printed at start of every run.
- Deterministic: same seed → same trace.

---

### Phase 12 Conclusion

This harness is the smallest artifact that can turn the theoretical boundary from Phases 9–11 into a concrete, reproducible measurement.

Once it exists and the vectors are run, we will know definitively whether a non-replenishable \( B_{\text{global}} \) is present or missing.

**Next action after harness exists:** execute Vectors A–G, record results, and open Phase 13 with the measured numbers.
