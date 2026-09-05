---
summary: "Snapshot then update every guest under a fleet root grant."
trigger: "Update all guests"
tier: "T2 snapshot + T2+ fleet root grant"
executor: "Proxmox snapshot API and host package manager"
rollback: "Snapshot rollback per affected guest"
---

# Runbook — update all guests

**Tier:** T2 snapshot + T2+ fleet root grant. **Trigger:** *"Update all guests."*

## Preconditions

- Build the guest order and exclusions from current inventory; request the fleet grant only after the plan is approved.

## Steps

1. **Plan from inventory:** order, reboot needs (kernel), pin exceptions. Present once; Ali
   approves the plan and issues `grant-root all 4h`.
2. **Per guest** (skip all pool-excluded guests):
   1. Proxmox snapshot (T2 — the role has `VM.Snapshot`/`VM.Snapshot.Rollback` for exactly this).
   2. `apt full-upgrade`.
   3. reboot **if** a new kernel was installed.
   4. health verify.
   5. **Failure → snapshot rollback + flag, continue with the rest.** Do not abort the run.
3. **Summary at the end**, interruptions only for failures. Commit refreshed inventory.

## Verify

- Record each guest's post-update health and reboot state; refresh inventory after the fleet pass.

## Rollback

- On a per-guest failure, roll back that guest's pre-update snapshot and continue with the approved plan.

## Evidence

- Commit refreshed inventory and record failures, rolled-back guests, and deferred exceptions.

> Renovate handles container image bumps separately (one PR per bump) — see [`deploy-service.md`](deploy-service.md).
