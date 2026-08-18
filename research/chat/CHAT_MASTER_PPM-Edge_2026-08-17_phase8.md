# Master Chat — PPM-Edge through Phase 8

**Updated:** 2026-08-17
**Constraint:** Production kernel frozen.

## Phase 8 result (final question)

**B — another numeric envelope that an informed optimizer can still exploit.**

When the adversary holds the origin-update token:
- Path length scales Θ(auth × origin_updates) or Θ(cum × origin_updates)
- min_cost_origin_2000 → path=40000, 0 policy rejects, 0 kernel protects
- origin_replenish_200cyc → path=100000
- auth_boundary_chatter_10k → path=200000 inside fixed origin box

When origin-update token is denied / origin frozen:
- Path still grows with event count but excursion is hard-capped at cum
- Spatial box is bounded; lifetime path is unbounded in time but confined in space

Controllability therefore reduces to: who may call origin-update, and how often?

## Artifacts
- PPM-Edge_adversarial_policy_phase8_2026-08-17.zip → Drive snapshots/
- This master → Drive chat_masters/
- results/phase8_policy_attack.json, reports/PHASE8_FINDINGS.md
