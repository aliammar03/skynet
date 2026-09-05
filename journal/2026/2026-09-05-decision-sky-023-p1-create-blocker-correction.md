---
date: 2026-09-05
kind: decision          # session | incident | decision
title: SKY-023 P1 create blocker correction
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023, SKY-024, PR #185, ADR 0005]
---

# 2026-09-05 · decision · SKY-023 P1 create blocker correction

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened

Ali challenged the Phase 1 claim that new-guest OpenTofu apply was blocked: he had successfully
provisioned an LXC the previous night. Re-read `scripts/tofu-apply.sh`, SKY-024 evidence, the trust
ladder, and the provisioning runbooks. The provider and operate token support guest creation; the
block came only from making the snapshot-before-update wrapper treat `create` like `update`.

The earlier reconciliation conflated the A4 admission rule with supervised T2 authority. ADR 0005
requires automatic, failure-tested rollback before a capability acts unattended at A4. It does not
forbid a human-approved T2 create. No infrastructure host, credential, plan, or apply was touched in
this correction.

## Actions & outcomes

- Changed `scripts/tofu-apply.sh` guest classification to carry `create|update`. Existing-guest
  updates still snapshot and fail closed when the snapshot cannot be taken. Creates skip the
  impossible pre-snapshot, emit a supervised/no-automatic-rollback warning, and apply only the exact
  saved plan already approved by the human checkpoint.
- Kept the delete/replace and excluded-guest refusals intact. A failed partial create is never
  auto-destroyed; the wrapper exits non-zero and requires operator inspection/recovery.
- Extended `tests/tofu-rollback-test.sh` with real create-shaped fixtures (`before: null`). Clean
  create applies with no snapshot; failed create takes no snapshot, performs no delete, and reports
  operator recovery. Existing update rollback tests remain unchanged.
- Replaced current-state blocker language in `AGENTS.md`, the constitution, architecture, actuator
  registry, runbook catalog, VM/LXC procedures, and `tofu/pool-cts.tf`. Historical journal entries
  were not rewritten.

## Graveyard — tried & abandoned

- Requiring automatic rollback before any supervised T2 guest create → abandoned because it applies
  the A4 admission criterion at A1/T2 and contradicts the proven SKY-024 provisioning path.
- Returning to bare re-planning `tofu apply` → rejected. The fixed wrapper preserves the exact saved
  plan, delete/excluded-guest guards, and deterministic post-apply verification.
- Auto-destroying a partial create → rejected because destruction remains a hard checkpoint at every
  autonomy level.

## Follow-ups / open threads

- Automatic create rollback is still required before guest creation can graduate to A4 unattended
  action. This does not block supervised T2 provisioning.
- Ali reviews and merges PR #185; Phase 2 remains out of scope until then.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
