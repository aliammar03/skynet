---
summary: "The L7 actuators and their rollback executors: what each write can undo, by whom, and how the rollback is decided deterministically."
tokens: 1648
---

# Spoke · Actuators & rollback executors

> Every actuator that writes state carries a **rollback executor**: a dumb, agent-independent way to
> undo the write. Governed by [`../system-design.md`](../system-design.md) and
> [ADR 0005 §3](../decisions/0005-full-agent-control-as-terminal-goal.md) (the reversibility test).
> Sourced from SKY-018 P6 (L7). The complementary *reachability* half of deploy hardening is SKY-016.

## The rule

The admission criterion for unattended action ([ADR 0005 §3](../decisions/0005-full-agent-control-as-terminal-goal.md))
is that a capability's rollback be **automatic**, **tested in the failure case**, and **independent
of the agent** — performed by a dumb executor that works even when the agent's judgement is the thing
that failed. Two consequences shape everything here:

- **The rollback DECISION is deterministic tooling, never the LLM.** A health probe, an exit code, a
  plan diff — the verdict is a comparison, not an opinion. The agent may *trigger* a gated action; it
  is never the thing that decides the action failed and must be undone.
- **Irreversible actions stay hard checkpoints at every level.** `destroy`, guest deletion, data
  deletion, credential rotation, anything T3 — a rollback executor does not make these auto-approvable.
  The tofu executor *refuses* them outright rather than trying to reverse them.

## The registry

| Actuator | Write path | Rollback executor | Decision (deterministic) | Independent-of-agent | Tested in failure |
|---|---|---|---|---|---|
| **Compose deploy** | `gitops-deploy.sh --gate` (Arcane GitOps) | `gitops-rollback.sh` — `git revert` the deploy commit → push → Arcane reconciles | `deploy-gate.sh` — every project container Running, not Restarting, healthy-or-none within the window | ✅ git + Arcane's dumb reconciler | `tests/compose-rollback-test.sh` · 2026-09-03 |
| **OpenTofu apply** | `tofu-apply.sh <saved-plan>` | snapshot-before-apply → `pve-snapshot.sh rollback` on failure | post-apply `tofu plan -detailed-exitcode` must be clean (+ optional verify hook) | ✅ Proxmox snapshot rollback (operate token) | `tests/tofu-rollback-test.sh` · 2026-09-03 |
| **DNS write** | `cf-dns-route.sh` (Cloudflare break-glass) | `dns-revert.sh undo` — replays the recorded **inverse** command | replay of a captured inverse (create⇒delete, update/delete⇒re-publish) | ✅ dumb replayer, re-runs a logged command | `tests/dns-revert-test.sh` · 2026-09-01 |
| deploy-rs (host cfg) | `nixos-rebuild`/deploy-rs | deploy-rs **magic-rollback** (built-in) | activation health check → auto-revert | ✅ platform | pre-existing (ADR 0005 ✅) |
| OPNsense config | (T2 via tofu, SKY-020) | OPNsense **validate-and-restore** (built-in) | config apply health → restore | ✅ platform | pre-existing (ADR 0005 ✅) |

**Destroy is not in this table by design.** `tofu-apply.sh` refuses any plan containing a
`delete`/replace action or touching a T3 excluded guest (5001, 635, 837, 2020) — those are human-run,
permanently ([Judgement Day §6](../system-design.md)).

### Live validation (2026-09-03)

Beyond the failure-injection harnesses, these ran against live infrastructure:

- **DNS** — full create → revert cycle against real Cloudflare (a throwaway `sky018-p6-canary`
  record): published, inverse recorded, replayed to delete, confirmed gone, log settled.
- **Snapshot create+delete+rollback** — exercised end-to-end on the live apps host
  `guest/docker-dmz-10015` via the operate token: a **vmstate** snapshot (RAM+disk, ~75s for 11.7 GB),
  a marker file written after it, then a **rollback** (~22s) that resumed the VM in place (SSH back in
  ~3s, all 18 containers healthy with uptimes preserved — a live-state resume, not a restart) and
  reverted the disk (marker gone), then snapshot pruned. The task-status check also correctly caught
  Proxmox refusing to snapshot the **template** VM 9000 — so a plan touching a template makes
  `tofu-apply.sh` **fail closed**, as designed.
- **Compose auto-revert (full)** — deliberately broke `librespeed` (a stateless service) with a
  crash-looping entrypoint on a throwaway branch and ran `gitops-deploy.sh --gate`: the gate detected
  the unhealthy deploy, `gitops-rollback.sh` git-reverted the break, and Arcane redeployed the reverted
  compose — librespeed auto-recovered to healthy and serving, **no human step**. This live rehearsal
  surfaced three bugs a stubbed harness could not: a transient Arcane sync 500 that aborted the deploy
  before the gate; a `set -e` trap in the healthcheck-coverage block that skipped the gate; and a
  rollback that only *nudged* the sync without a redeploy, so a crash-looping service stayed down after
  the revert landed in git. All three fixed (sync retry, `|| true` guard, force-redeploy on rollback).

Notes on the snapshot rollback: it uses **vmstate** (`PVE_SNAPSHOT_VMSTATE=1`) for a running guest so
the rollback resumes in place instead of a stop/start outage — heavier (writes RAM to disk) but
seamless. A rollback still reverts *every* disk write in the snapshot window, so for a live DB host it
is a real data-loss event for that window; `tofu-apply.sh` keeps it bounded by snapshotting
immediately before the apply and rolling back immediately on failure.

## Notes that are load-bearing

- **Saved plan only.** `tofu-apply.sh` applies the exact plan file that was reviewed (`tofu plan -out`);
  it never re-plans at apply time, so the diff that ran is the diff that was seen.
- **Fail closed.** If `tofu-apply.sh` cannot snapshot a touched guest (e.g. an NFS-backed LXC that
  can't be snapshotted), it refuses to apply — no rollback point means no change.
- **The compose gate probes the service's own declared endpoint** (the compose healthcheck the skynet
  service standard already requires), so the gate adds a *decision*, not a new contract.
- **DNS records under tofu** (`tofu/dns-*.tf`, `tofu/cloudflare-dns.tf`) roll back through the tofu
  path (revert the source + `tofu-apply.sh`); `dns-revert.sh` covers the imperative break-glass write.

## Where this is going

This registry is the substrate SKY-018 P6 built. **SKY-017 P1** extends it into the per-capability
**autonomy track record** — each executor's failure-case rehearsals in the proving ground become the
recorded evidence that buys a promotion up the A0–A5 ladder. An actuator with no row here cannot reach
A4.
