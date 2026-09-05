---
summary: "The L7 actuators and their rollback executors: what each write can undo, by whom, and how the rollback is decided deterministically."
---

# Spoke · Actuators & rollback executors

> This registry states which write actuators have a **rollback executor**: a dumb,
> agent-independent way to undo the write. An actuator without one remains supervised and cannot
> reach A4. Governed by [`../system-design.md`](../system-design.md) and
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
| **Compose deploy** | `gitops-deploy.sh --gate` (Arcane GitOps) | `gitops-rollback.sh` — reports failure by default; explicit `--prepare` creates a revert in an isolated review branch | `deploy-gate.sh` — every project container Running, not Restarting, healthy-or-none within the window | ❌ authored revert requires explicit operator preparation and human merge | `tests/compose-rollback-test.sh` · 2026-09-05 |
| **OpenTofu existing-guest update** | `tofu-apply.sh <saved-plan>` | snapshot-before-apply; an API apply failure may roll back, while a post-apply verification/dirty-plan failure preserves the snapshot and escalates operator recovery | post-apply `tofu plan -detailed-exitcode` + verification must be clean | ❌ partial safety only; not A4-eligible | `tests/tofu-rollback-test.sh` |
| OpenTofu guest create (supervised T2 only) | `tofu-apply.sh <saved-plan>` after explicit approval | **none** — no pre-change guest exists; never auto-destroy a partial create | post-apply plan is checked, but failure needs operator recovery | ❌ | guarded behavior: `tests/tofu-rollback-test.sh` |
| OpenTofu non-guest create/update (including DNS) | `tofu-apply.sh <saved-plan>` (supervised only) | **none** — the wrapper has no non-guest snapshot/inverse | post-apply plan is checked, but a failure still needs operator recovery | ❌ | ❌ |
| **DNS write** | `cf-dns-route.sh` (Cloudflare break-glass) | `dns-revert.sh undo` — replays a durably recorded **full-record inverse** | inverse captured before mutation; create⇒absent, update/delete⇒restore prior fields | ✅ dumb replayer; writer fails closed if inverse logging fails | `tests/dns-revert-test.sh` · 2026-09-05 |
| deploy-rs (host cfg) | `nixos-rebuild`/deploy-rs | deploy-rs **magic-rollback** (built-in) | activation health check → auto-revert | ✅ platform | pre-existing (ADR 0005 ✅) |
| OPNsense config (planned, not live) | pending SKY-020 | planned OPNsense validate-and-restore path | not implemented | — | ❌ |

**Destroy is not in this table by design.** `tofu-apply.sh` refuses any plan containing a
`delete`/replace action or touching a T3 excluded guest (5001, 635, 837, 2020) — those are human-run,
permanently ([Judgement Day §6](../system-design.md)).

**New-guest create is a supervised T2 action.** The wrapper recognizes a create and
does not attempt the impossible pre-snapshot. The exact saved plan still requires explicit approval,
and a failed partial create needs operator recovery. Without an automatic, failure-tested rollback,
this actuator cannot graduate to A4.

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
- **Compose health gate (live rehearsal)** — a throwaway `librespeed` crash-loop proved the gate can
  detect an unhealthy deploy. The earlier direct-push recovery path was retired because authored
  reverts must stay human-merged; the current gate reports failure and an operator may explicitly
  prepare an isolated review branch.

Notes on the snapshot rollback: it uses **vmstate** (`PVE_SNAPSHOT_VMSTATE=1`) for a running guest so
the rollback resumes in place instead of a stop/start outage — heavier (writes RAM to disk) but
seamless. A rollback still reverts *every* disk write in the snapshot window, so for a live DB host it
is a real data-loss event for that window; `tofu-apply.sh` keeps the recovery point bounded by
snapshotting immediately before the apply. Apply/API failures can roll back; verification failures
preserve the snapshot and require operator recovery.

## Notes that are load-bearing

- **Saved plan and one actuator only.** `tofu-apply.sh` applies the exact plan file (`tofu plan -out`)
  and rejects a mixed/mismatched `TOFU_APPLY_SCOPE`; it never re-plans at apply time. Human merge and
  exact-plan approval remain explicit operator checkpoints—the wrapper cannot authenticate who gave
  that approval or prove the plan was created from a merged revision.
- **Fail closed for updates.** If `tofu-apply.sh` cannot snapshot an existing guest being updated
  (e.g. an NFS-backed LXC that cannot be snapshotted), it refuses to apply. A provider/API apply
  failure may use the preserved snapshot rollback path; a post-apply verification or dirty-plan
  failure keeps the snapshot for operator inspection and recovery. Creates are separately classified
  as supervised actions with no automatic rollback.
- **The compose gate probes the service's own declared endpoint** (the compose healthcheck the skynet
  service standard already requires), so the gate adds a *decision*, not a new contract. On failure it
  reports rollback required without mutating the deploy checkout; an operator may explicitly prepare
  an isolated review branch, and authored changes remain human-merge gated.
- **Non-guest writes are not snapshot-rolled back.** `tofu-apply.sh` still enforces the saved plan,
  delete guard, and post-apply check for DNS, but it has no automatic inverse for those resources.
  They remain supervised below A4 until a failure-tested rollback exists.
- **A source revert that removes a tofu resource produces a delete plan, which the wrapper refuses.**
  DNS removal therefore uses an explicit hard-checkpoint path; `dns-revert.sh` covers Cloudflare's
  imperative break-glass writer. Do not describe a deletion as a `tofu-apply.sh` rollback.

## Where this is going

This registry is the substrate SKY-018 P6 built. **SKY-017 P1** extends it into the per-capability
**autonomy track record** — each executor's failure-case rehearsals in the proving ground become the
recorded evidence that buys a promotion up the A0–A5 ladder. An actuator with no row here cannot reach
A4.
