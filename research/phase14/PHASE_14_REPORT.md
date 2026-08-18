# Phase 14 — FormalPolicy + non-replenishable \(B_{\text{global}}\)

**Date:** 2026-08-17  
**Production kernel:** FROZEN (research harness only)

## Change under test

Add to FormalPolicy:

1. Config `b_global` (default 100 000 in this run)
2. On move: reject if `total_path + |Δ| > b_global` (reason `b_global`)
3. Origin update **does not** reset `total_path`
4. Optional `origin_update_cost` can charge path (left at 0 here)

## Results

| Case | Path | Origins | b_global rejects | Verdict |
|------|-----:|--------:|-----------------:|---------|
| fixed_origin_oscillation_10k | 99 997 | 0 | 4737 | PASS — capped |
| min_cost_origin_2000 | 38 000 | 2000 | 0 | PASS — under budget |
| full_budget_replenish_200 | 98 800 | 200 | 0 | PASS — under budget (same as Phase 13 length) |
| **full_budget_replenish_extended** (207 cycles) | **99 997** | 207 | **119** | **PASS — capped** |
| origin_denied_2000 | 494 | 0 | 0 (cum_disp) | PASS |
| tiny_chatter_150k | 100 000 | 0 | 50 000 | PASS — capped |
| authority / spatial violations | — | — | — | PASS (unchanged) |
| honest short / origin rebase / near-budget | under budget | — | 0 | PASS — no false rejects |
| budget_survives_reauth | 99 997 | — | 837 | PASS |

## Comparison to Phase 13

Without \(B_{\text{global}}\), `full_budget_replenish_200` reached path ≈ 98 800 with **zero** path-budget rejects and would continue unbounded as cycles increase.  

With \(B_{\text{global}}=100\,000\), the extended replenish attack stops at path ≤ budget and accumulates `b_global` rejects. Origin rebase no longer replenishes global path.

## Conclusion

**A non-replenishable global path budget closes the Phase 13 gap** on the FormalPolicy layer. Honest traffic below the budget is unaffected in these vectors.

Recommended next steps:

- Tune default \(B_{\text{global}}\) and optional `origin_update_cost` for product envelopes
- Latency characterization of the extra check (integer add + compare)
- If productizing: keep production kernel frozen; implement policy as an external gate

## Artifacts

- `formal_policy_bglobal.py` — policy with \(B_{\text{global}}\)
- `phase14_formal_policy_redteam.py` — runner
- `PHASE_14_RESULTS.json` — full machine-readable results
