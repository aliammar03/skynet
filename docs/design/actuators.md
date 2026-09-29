---
summary: "The current write actuators, deterministic rollback paths, and A4 eligibility of each capability."
---

# Spoke · Actuators & rollback executors

> The current registry of write paths and their recovery boundaries. Governed by
> [`../system-design.md`](../system-design.md) and the reversibility test in
> [ADR 0005](../decisions/0005-full-agent-control-as-terminal-goal.md).

Unattended action requires an automatic failure-tested rollback performed by a deterministic executor,
not an LLM. Every Skynet write runs one shape (`src/skynet/writepath.py`): plan → preflight →
snapshot → execute → verify → rollback or stop → record, under a lock (`write` for the service
paths, `tofu` for OpenTofu, so a long apply never delays a deploy), with an append-only
record in `/opt/skynet-ops/state/operations.jsonl`; an interrupted write is reconciled before the
next one on its target. Irreversible work remains a hard checkpoint. The executor rejects tofu delete/replace
plans and T3-excluded guests rather than attempting to make them reversible.

| Actuator | Write path | Recovery on failure | Deterministic decision | A4 eligible |
|---|---|---|---|---|
| Compose deploy | `skynet deploy <svc>` / `--pending` (merged revisions only) | Automatic redeploy of the host's `verified` revision, `failed` marker, revert PR | Deployment verifier: every container at the `skynet.revision`, running, healthy; declared routes answer | Yes (A4) |
| Existing-guest tofu update | `skynet tofu apply <stack>` / `--pending` (merged, hash-approved) | Each guest's config saved before apply (plus a disk-only snapshot, the operator's fallback, except of a container with a bind mount, which Proxmox cannot snapshot); on apply failure, or a re-plan that still wants the approved change, write every guest's saved config back (continuing past a failure), return it to its prior power state, observe it, then restore the pre-apply state; a failure is held in git | Clean post-apply plan | Supervised (A3); A4 after the live LXC and VM rollback drills |
| Tofu guest create | `skynet tofu apply` (merged, hash-approved) | None; never auto-destroy a partial create; held in git and alerts | Clean post-apply plan | Supervised; no automatic inverse |
| Tofu non-guest write (DNS records, templates) | `skynet tofu apply` (merged, hash-approved) | None; held in git and alerts | Clean post-apply plan | Supervised; no automatic inverse |
| Authentik publish | `skynet publish <svc>` (additive provider/application/outpost binding) | Deletes only the objects the run created; restores the outpost's provider list | Anonymous probe redirects to the login | No |
| Public route withdraw | `skynet withdraw <vhost> --confirm <vhost>` (git must no longer declare it) | Re-creates a deleted CNAME from its snapshot; Authentik objects are re-made by `publish` | Records absent after the run | No — a delete stays a hard checkpoint |
| NixOS deployment | deploy-rs / `nixos-rebuild` | deploy-rs magic rollback | Activation health check | Yes |
| OPNsense config | No live actuator | None | — | No |

The Tofu executor applies only the plan it makes from the merged revision, and only when that plan's
normalized-change hash equals the PR's `approved-plan.json`. The hash covers each change's actions and
the attributes it moves (before → after); refresh values of untouched attributes, such as a guest
agent's IP lists, stay out, and an attribute known only after apply is bound by name. A failure is
rolled back only when every change was an updated guest's restorable attributes or a state-only move;
anything else keeps its snapshots, records the state OpenTofu wrote, and alerts. Rollback is a config
restore, never a snapshot rollback: a guest's disk and RAM hold payload data written since. Only the
keys that differ are written back, keys the apply added are deleted, the config digest makes the write
a compare-and-swap, and a running guest reboots only when changes are left pending. A guest update
is rolled back only when every attribute it changes is one the restore sets back (`RESTORE_COVERS`);
pool membership, disk size, or a template conversion has no automatic inverse. A guest with pending
changes before the apply is refused. Every rollback is then proved: the guest's whole config must
equal its pre-apply copy with nothing pending, or the run is `rollback-failed` (alert, hold, snapshot
kept). A dirty post-apply plan rolls back only when it still wants an (address, attribute) the approved
change moved; one dirty only elsewhere (drift, a provider's perpetual diff) is never rolled back: it
alerts and holds, as does a post-apply check that cannot run. An apply updates at most five existing
guests, so a hung apply plus its full rollback fits the `skynet-tofu` unit's 5 h budget; a pass
defers a stack it cannot finish. A revision is held in git before it executes, and only its recorded
success clears the hold; every hold alerts once, however it was set (an unreadable `held.json` holds
every revision until a supervised `--ignore-hold` success; a hold no run announced alerts on the next
pass). A snapshot that cannot be made refuses the
apply (and one a failed create left behind is cleaned up, or the revision is held); one that fails to
delete is queued, retried each pass, and alerts. Each snapshot is recorded before it is requested, so
one left by a crash is found and cleaned; a queued entry naming an excluded guest is dropped and
alerts, and every Proxmox write refuses an excluded guest itself. An apply that times out is
indeterminate (its process group is killed; remote work may still land): never rolled back, it keeps
its snapshots, holds, and alerts. Each pass first pushes any state the branch lacks, under the tofu
lock and even for a held revision, without re-running the apply. A first local state (no branch,
no recorded base) is pushed only after an apply at its stack has planned it and passed every
refusal. `plan --approve` makes the same refusals, so a PR never carries an approval the executor
would hold. Excluded guests are the union of the revision's and main's lists.

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
