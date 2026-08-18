# Master Chat Session Record — PPM-Edge (through Phase 7)

**Updated:** 2026-08-17  
**Constraint:** Production kernel frozen; isolated experimental layer only.

## Session progress

- Prior phases 1–6 completed and archived.
- User supplied full research brief (threshold surface, attack sequences, minimal policy, red-team, evidence rules).
- Phase 7 executed:
  - 7a: Deep threshold-hugging surface (grid + 80k/40k streams + initial states)
  - 7b: Attack sequences with event-by-event traces (9 patterns)
  - 7c: Policy ablation one-at-a-time
  - 7d: Red-team bare vs auth+cum
- C adversarial harness re-run: ALL PASS
- Snapshot uploaded to Google Drive `snapshots/`
- This master record saved to `chat_masters/`

## Answers to the final research questions

1. **Harmful trajectory while compliant:** Every sub-threshold cell (k≥1) yields 0% PROTECT. 80k-step uni stream at th=20 → path 1.52M, net 1.52M, 0 protections.
2. **Minimum additional policy:** `authority_delta` + `cum_disp_limit`.
3. **Which holes closed:** Slow drift, large hugs, boundary camping largely closed by authority; unbounded net by cum_disp. Residual chatter inside the authority band remains.
4. **Tradeoffs:** Origin dependence on long ramps (legit_ramp rejected ~90–97% once past cum limit); chatter limits have high FP; no semantic intent check; negligible latency for auth+cum.
5. **Outside scope:** In-band residual attacks, goal appropriateness, contradiction semantics, world models.
6. **Controllability vs informed adversary:** Numeric envelopes can be respected while still producing substantial path/chatter. Architecture remains a last numeric interlock, not a semantic guard.

## Drive artifacts

- `PPM-Edge_adversarial_policy_phase7_2026-08-17.zip` → snapshots/
- This file → chat_masters/
