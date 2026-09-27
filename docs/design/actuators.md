---
summary: "The current write actuators, deterministic rollback paths, and A4 eligibility of each capability."
---

# Spoke · Actuators & rollback executors

> The current registry of write paths and their recovery boundaries. Governed by
> [`../system-design.md`](../system-design.md) and the reversibility test in
> [ADR 0005](../decisions/0005-full-agent-control-as-terminal-goal.md).

Unattended action requires an automatic failure-tested rollback performed by a deterministic executor,
not an LLM. Every Skynet write runs one shape (`src/skynet/writepath.py`): plan → preflight →
snapshot → execute → verify → rollback or stop → record, under one lock, with an append-only
record in `/opt/skynet-ops/state/operations.jsonl`; an interrupted write is reconciled before the
next one on its target. Irreversible work remains a hard checkpoint. The executor rejects tofu delete/replace
plans and T3-excluded guests rather than attempting to make them reversible.

| Actuator | Write path | Recovery on failure | Deterministic decision | A4 eligible |
|---|---|---|---|---|
| Compose deploy | `skynet deploy <svc>` / `--pending` (merged revisions only) | Automatic redeploy of the host's `verified` revision, `failed` marker, revert PR | Deployment verifier: every container at the `skynet.revision`, running, healthy; declared routes answer | Yes (A4) |
| Existing-guest tofu update | `skynet tofu apply <stack>` / `--pending` (merged, hash-approved) | Proxmox snapshot before apply; on apply or verify failure, roll back every guest (continuing past a failure) to its snapshot and prior power state, observe it, then restore the pre-apply state; a failure is held in git | Clean post-apply plan | Yes (A4) |
| Tofu guest create | `skynet tofu apply` (merged, hash-approved) | None; never auto-destroy a partial create; held in git and alerts | Clean post-apply plan | Unattended on merge; no automatic inverse |
| Tofu non-guest write (DNS records, templates) | `skynet tofu apply` (merged, hash-approved) | None; held in git and alerts | Clean post-apply plan | Unattended on merge; no automatic inverse |
| Authentik publish | `skynet publish <svc>` (additive provider/application/outpost binding) | Deletes only the objects the run created; restores the outpost's provider list | Anonymous probe redirects to the login | No |
| Public route withdraw | `skynet withdraw <vhost> --confirm <vhost>` (git must no longer declare it) | Re-creates a deleted CNAME from its snapshot; Authentik objects are re-made by `publish` | Records absent after the run | No — a delete stays a hard checkpoint |
| NixOS deployment | deploy-rs / `nixos-rebuild` | deploy-rs magic rollback | Activation health check | Yes |
| OPNsense config | No live actuator | None | — | No |

The Tofu executor applies only the plan it makes from the merged revision, and only when that plan's
normalized-change hash equals the PR's `approved-plan.json`. A failure is rolled back only when every
change was a snapshotted guest update or a state-only move; anything else keeps its snapshots,
records the state OpenTofu wrote, and alerts. A snapshot that cannot be made refuses the apply (and one a failed create left behind is
cleaned up, or the revision is held). A guest update is rolled back only when every attribute it
changes is one a snapshot restores (`SNAPSHOT_COVERS`); pool membership, disk size, or a template
conversion has no automatic inverse. A post-apply check that cannot run leaves the change
unverified: it alerts and holds, never rolls back. An apply updates at most five existing guests,
so a hung apply plus its full rollback fits the deploy unit's 4 h budget; the timer defers a
stack it cannot finish.

Automated rollback proof lives in the local test suite (`tests/`, run by `bin/check`): an actuator
claims an A4 promotion only when its failure-case rollback is exercised there and recorded live.
Historical rehearsal evidence remains in the journal.

## OpenTofu stacks and state

OpenTofu 1.11.8; providers bpg/proxmox 0.111.1, cloudflare/cloudflare 5.24.0, kevynb/technitium
0.4.0, each pinned by its stack's `.terraform.lock.hcl`. Each stack's state is encrypted (PBKDF2 +
AES-GCM, passphrase from sops) at `/opt/skynet-ops/state/tofu/<stack>.tfstate` and mirrored, with
`<stack>/applied.json` (revision, hash, operation), to the `tofu-state` branch. The branch is the
truth: a missing or stale local file is rebuilt from it, and a diverged one is refused. A held
revision is `<stack>/held.json` on the same branch, so a hold survives an ops VM rebuild; a success
clears it.

| Stack | Inputs beyond `tofu/<stack>/` | Resources |
|---|---|---|
| `proxmox-core` | — | `proxmox_virtual_environment_container.pbs`, `…container.pool_ct["adguard-core"]`, `…container.core_ct["athena"]`, `proxmox_virtual_environment_vm.docker_dmz`, `…vm.ubuntu_2404_base` |
| `technitium-dns` | `compose/caddy-apps/Caddyfile` | `technitium_record.aliammar_net[*]` (10 vanity names), `technitium_record.apps_service[*]` (one per apps vhost) |
| `cloudflare-dns` | `compose/cloudflared/config.yml` | `cloudflare_dns_record.tunnel[*]` (one per public host) |

`proxmox-network` has no declared resource; its stack is created with its first one. The
pre-split root state is kept at `/opt/skynet-ops/state/tofu/legacy/` until SKY-025 Phase 18.
