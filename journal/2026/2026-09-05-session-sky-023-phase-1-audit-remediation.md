---
date: 2026-09-05
kind: session          # session | incident | decision
title: SKY-023 Phase 1 audit remediation
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023, SKY-024, PR #185]
---

# 2026-09-05 · session · SKY-023 Phase 1 audit remediation

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
The prior Phase 1 close-out recorded a false blocker on OpenTofu-created LXCs. The existing
saved-plan executor already allowed a supervised create, while the directive/prose treated all
creates as unavailable because A4 automatic rollback does not exist for a new object. This session
corrected that distinction and audited the adjacent delegated-review findings before Phase 1 was
closed again. No infrastructure command, provider plan/apply, credential read, or root grant ran.

The audit also found direct authored-revert pushing in the Compose health path; lossy Cloudflare DNS
inverses; unsafe state/snapshot recovery assumptions; broad per-host SSH certificate offering;
unpooled core CTs described as pool-managed; imported-resource lifecycle ignores copied to native
guests; stale provisioning/Authentik/PBS/template claims; and active SKY-024 instructions that still
showed bare apply/destroy commands.

## Actions & outcomes
- Reworked `scripts/gitops-rollback.sh` and its gate/test → unhealthy Compose deployments now report
  or prepare an isolated local review branch; no authored revert is pushed or merged by the agent.
- Reworked Cloudflare inverse recording and DNS tests → capture the full writable prior record before
  mutation; an inverse-log write failure prevents the mutation.
- Hardened `scripts/tofu-apply.sh`, `scripts/tofu-env.sh`, and rollback tests → require one named
  actuator scope, reject mixed plans, load only that scope at apply time, snapshot existing guests,
  restore matching OpenTofu state only after successful guest rollback, and retain snapshots when
  verification is dirty or unavailable.
- Added the excluded-guest guard and VM-state default to `scripts/pve-snapshot.sh` → helper refuses
  every invariant-excluded VMID, including Unraid 2020, before calling Proxmox.
- Split imported and native core CT declarations → compatibility ignores remain only on imports;
  native Athena fields are actionable and the state move preserves its address.
- Corrected the root certificate selector → generated SSH config now has one `Host <host>` stanza
  per grant instead of a broad `Match user root` block that offered every cert.
- Reconciled current docs/runbooks/directives to the executable behavior and added regression tests
  for Compose rollback, DNS revert, saved-plan rollback, snapshots, provisioning truth, and cert
  selection.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Treating a failed or unavailable post-apply verifier as automatic-rollback evidence → abandoned;
  a successful apply may have unknown remote effects, so snapshots stay for an operator.
- Restoring pre-apply OpenTofu state after any snapshot rollback failure → abandoned; it could hide
  a remote guest that did not return to its pre-apply state.
- Leaving the global SSH `Match user root` selector as legacy compatibility → abandoned; OpenSSH may
  offer multiple certificates and hit `MaxAuthTries` before reaching the correct one.

## Follow-ups / open threads
- Phase 1 remains T1 repository remediation. Provider-root/state separation for plan creation and
  a failure-tested automatic inverse for newly created guests remain future work; neither is claimed
  as A4-ready.
- PR #185 needs normal human review, CI confirmation, and merge. The agent must not merge it.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
