# PHASE 10 — BOUNDARY STRESS & BUDGET EVASION
## PPM-Edge External Policy Analysis (Production Kernel Frozen)

**Date:** 2026-08-16 / 2026-08-17  
**Status:** Production source untouched  
**Scope:** Numeric/capability layer only

---

### Objective
Assuming the strongest pure-numeric model from Phase 9 (non-replenishable global path budget \(B_{\text{global}}\) + constrained origin-update capability), attempt to violate or circumvent the finite bound on lifetime activity \(\sum|\Delta|\).

### 10.1 Attack Surface Against \(B_{\text{global}}\)

| Attack Vector | Description | Expected Outcome if Bound Holds |
|---------------|-------------|---------------------------------|
| A. Session restart | Force new session after exhausting budget | Budget must not reset |
| B. Recovery / checkpoint restore | Restore from earlier state | Budget must survive restore |
| C. Authority change / re-authentication | New higher-privilege context | Budget must remain global |
| D. Integer / fixed-point overflow | Extremely large number of tiny \(\Delta\) | Summation must not wrap |
| E. Measurement quantization | Use \(\Delta\) smaller than resolution | Must still accumulate correctly |
| F. Parallel / concurrent streams | Multiple simultaneous sources of \(\Delta\) | Must share the same global budget |
| G. Origin-update + movement interleaving | Rapid origin updates mixed with oscillation | Origin budget + path budget both enforced |
| H. Long-duration low-amplitude chatter | Continuous \(\pm 1\) or \(\pm(\text{authority_delta}-1)\) for extended time | Path must hit \(B_{\text{global}}\) and stop |

### 10.2 Constructive Oscillation Under Strongest Policy

Even with origin updates fully disabled and a hard \(B_{\text{global}}\):

- Adversary emits \(\Delta = \pm(\text{authority_delta}-1)\) repeatedly.
- Spatial constraint \(|\text{value}-\text{origin}| \le \text{cum_disp_limit}\) remains satisfied.
- Path length grows as \(N \times (\text{authority_delta}-1)\).
- Acceptance continues until \(\sum|\Delta| = B_{\text{global}}\).
- After that point every further event must be rejected.

This confirms that the **only** finite lifetime activity bound is the explicit global path budget itself. Spatial envelope alone never bounds activity.

### 10.3 What Still Escapes Any Pure Numeric Bound

Even under the strongest configuration above, the following remain unbounded or uncontrolled:

1. **Semantic content** of the trajectory (intent, meaning, downstream effects).
2. **Side-channel activity** not expressed as measured \(|\Delta|\) events (timing, external I/O, resource consumption outside the state machine).
3. **Any resource the kernel does not meter**.
4. **Collusion across multiple independent instances** if each has its own \(B_{\text{global}}\).

### 10.4 Minimal Complete Bound (Numeric Layer)

The smallest configuration that actually delivers finite bounds on **both** space and lifetime activity is:

```
non-replenishable global path budget B_global
+ origin-update capability that is either:
    - completely disabled, or
    - itself non-replenishable, non-replayable, non-transferable, and budgeted
+ no budget-reset path through recovery, session, or authority change
```

Anything weaker leaves at least one of the two resources (space or activity) unbounded.

### 10.5 Remaining Open Questions

- Can the global budget itself be made adaptive or hierarchical without introducing a reset path?
- What is the precise false-rejection cost of a tight \(B_{\text{global}}\) under realistic legitimate workloads?
- How does the bound compose when multiple PPM-Edge instances interact?

### Conclusion
We have stress-tested the strongest pure-numeric authority model. The bound holds **if and only if** the global path budget is truly non-replenishable and origin authority is independently constrained. Spatial envelopes alone are insufficient. Semantic and side-channel channels remain outside the numeric model.
