# PHASE 9 — AUTHORITY/CAPABILITY RED TEAM
## PPM-Edge External Policy Analysis (Production Kernel Frozen)

**Date:** 2026-08-16 / 2026-08-17  
**Status:** Production source untouched  
**Scope:** Numeric/capability layer only (no semantic/AI-intent controls)

---

### Scope and Constraints
- Production PPM-Edge kernel remains untouched.
- Analysis limited to the numeric/capability layer (origin authority, cumulative displacement, path length).
- Goal: determine the minimal authority model that yields a finite bound on **both** spatial excursion and lifetime cumulative activity (Σ|Δ|).

### 1. Modeling Origin-Update as a Capability

Treat `origin_update` as a discrete security capability with the following attributes:

| Attribute       | Meaning                                      |
|-----------------|----------------------------------------------|
| Issuer          | Who may mint or grant the token              |
| Lifetime        | Temporal validity window                     |
| Scope           | Which origins / values it can affect         |
| Reuse           | Whether a single token can be consumed >1×   |
| Replay          | Whether a previously used token can be re-presented |
| Sequence        | Ordering constraints relative to movement events |
| Budget          | Maximum number of updates or total origin displacement permitted |
| Transferability | Whether the token can be delegated           |
| Survival        | Whether the token survives reset / recovery / session boundary |

### 2. Token Reuse and Replay Attacks

Under an unrestricted or weakly scoped origin-update token:

- Unlimited reuse of one valid token → unbounded origin repositioning.
- Replay of an old token → same effect as reuse if no nonce or sequence number is enforced.
- Duplicate / delayed / reordered updates → each successful origin update can reset the spatial envelope relative to a new origin.
- Result: each successful origin update can inject up to `authority_delta` (or the configured max origin displacement) of additional spatial budget. With sufficient updates the spatial envelope can be walked arbitrarily far and the cumulative path Σ|Δ| grows without bound.

**Conclusion**: A reusable or replayable origin-update token is equivalent to an unbounded spatial and activity resource.

### 3. Rate-Limit Evaluation

| Limit Type                          | Effect                        | Residual Path Bound                  |
|-------------------------------------|-------------------------------|--------------------------------------|
| Max updates / second                | Limits instantaneous rate     | Still unbounded over long time       |
| Max updates / minute                | Same                          | Still unbounded over long time       |
| Max updates / session               | Finite per session            | Unbounded across sessions if sessions can be restarted |
| Cooldown between updates            | Limits frequency              | Unbounded over long time             |
| Cumulative origin-update displacement budget | Caps total origin movement | Finite if the budget itself is non-replenishable |

Rate limits alone convert an unbounded resource into a *rate-bounded* resource. They do **not** produce a finite lifetime path bound unless combined with a non-replenishable global budget or hard session lifetime.

### 4. Global Non-Replenishable Path Budget

Define a global lifetime path budget:

\[
B_{\text{global}} \quad\text{such that}\quad \sum |\Delta| \le B_{\text{global}}
\]

- If any of origin updates, authority changes, recovery, resets, or session boundaries can reset or replenish \(B_{\text{global}}\), the bound collapses.
- Only a budget that is strictly non-replenishable (persists across all those events) yields a true finite lifetime path bound.

### 5. Policy Variant Comparison

| Variant | Spatial Bound | Lifetime Path Bound | Notes |
|---------|---------------|---------------------|-------|
| A. Fixed origin + cumulative budget | Finite | Finite (under fixed origin) | Oscillation still allowed up to the cumulative budget |
| B. Cumulative budget + unrestricted origin updates | Unbounded | Unbounded | Origin updates replenish spatial allowance |
| C. Cumulative budget + rate-limited origin updates | Rate-limited | Unbounded over long time | Rate limits do not cap lifetime |
| D. Cumulative budget + finite origin-update budget | Finite | Finite | Origin-update budget must itself be non-replenishable |
| E. Cumulative budget + non-replenishable global path budget | Finite | Finite | Strongest pure numeric bound |
| F. Higher-authority origin updates + finite global budget | Finite | Finite | Requires the global budget to be outside the authority of the origin-update issuer |

### 6. Bounded-Oscillation Attack (Origin Updates Disabled)

Even with origin updates completely disabled:

- An adversary can still emit a stream of ±(authority_delta − 1) steps.
- While |value − origin| ≤ cum_disp_limit, the cumulative path Σ|Δ| grows linearly with the number of accepted events.
- With no global lifetime path budget, Σ|Δ| is **unbounded**.

A spatial envelope is therefore **not** an activity/trajectory bound.

### 7. Legitimate Behavior

Under a properly configured non-replenishable global path budget + finite origin-update budget:

- Walking-like movement, long ramps, and reversals are accepted until the global budget is exhausted.
- Legitimate origin changes consume the origin-update budget.
- False-rejection rate is determined by how tightly the budgets are set relative to expected legitimate activity. Overly tight budgets increase false rejection; the trade-off is explicit and measurable.

### 8. Formal Results

**Maximum lifetime path** is finite if and only if a non-replenishable global path budget \(B_{\text{global}}\) exists and is enforced across all state transitions (including origin updates, resets, and recoveries).

**Maximum spatial excursion** is finite under a fixed or budgeted origin model.

**Maximum origin-update count / displacement** is finite only when the origin-update capability itself carries a non-replenishable budget.

**Conditions required for a joint finite bound**:
1. Non-replenishable global path budget \(B_{\text{global}}\).
2. Origin-update capability that is either disabled or itself budgeted (count and/or displacement) and non-transferable / non-replayable.
3. No budget-reset path through recovery, session restart, or authority change.

**What remains unbounded even under the strongest pure numeric model**:
- Semantic intent (what the movement *means*).
- Side-channel or external-channel activity outside the numeric state machine.
- Any resource not captured by the measured |Δ| events.

### 9. Evidence Discipline
- Production source remains frozen.
- All attack constructions, configurations, and results are recorded as experimental artifacts only.
- V1 correctness gates should be re-run after any experimental instrumentation to confirm no production side-effects.

---

### FINAL ANSWER

**Smallest authority model that yields a finite bound on both spatial excursion and lifetime cumulative activity**:

- A **non-replenishable global path budget** \(B_{\text{global}}\) that is enforced on every accepted |Δ| event and survives origin updates, resets, recoveries, and session boundaries,
- combined with either  
  (a) origin updates completely disabled, or  
  (b) origin updates themselves carrying a finite, non-replenishable, non-replayable, non-transferable budget (count and/or displacement).

Under this model both space and lifetime activity are finite.

**What remains unbounded**:
- Any activity not expressed as the measured |Δ| events.
- Semantic / intentional content of the trajectory.
- External or side-channel resources.

Spatial bounding alone is insufficient; activity bounding requires an explicit non-replenishable path budget. Origin-update authority must be treated as a first-class capability and independently constrained, or the spatial envelope can be walked indefinitely.

Phase 9 result is a precise control-theoretic boundary rather than an additional defensive patch.

---

**Phase 8 Reference (from prior analysis)**  
With authority_delta=20, a ±19 oscillator can accumulate 1.9 million path units over 100,000 accepted events while remaining inside a fixed ±500 spatial envelope. With authorized rebasing, 2,000 × 20 gives 40,000 path units.  
Policy bounds position, but does not necessarily bound activity over time. Origin authority is effectively a capability to replenish the allowable trajectory.
