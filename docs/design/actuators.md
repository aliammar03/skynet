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
| Existing-guest tofu update | `tofu-apply.sh <saved-plan>` | Snapshot before apply; preserve snapshot for verification/dirty-plan recovery | Post-apply plan and verification | No |
| Tofu guest create | Approved `tofu-apply.sh <saved-plan>` | None; never auto-destroy partial create | Post-apply plan | No |
| Tofu non-guest write | Approved `tofu-apply.sh <saved-plan>` | None | Post-apply plan | No |
| Authentik publish | `skynet publish <svc>` (additive provider/application/outpost binding) | Deletes only the objects the run created; restores the outpost's provider list | Anonymous probe redirects to the login | No |
| Public route withdraw | `skynet withdraw <vhost> --confirm <vhost>` (git must no longer declare it) | Re-creates a deleted CNAME from its snapshot; Authentik objects are re-made by `publish` | Records absent after the run | No — a delete stays a hard checkpoint |
| NixOS deployment | deploy-rs / `nixos-rebuild` | deploy-rs magic rollback | Activation health check | Yes |
| OPNsense config | No live actuator | None | — | No |

The saved-plan wrapper applies one approved scope and never re-plans. Existing-guest updates fail
closed when a snapshot cannot be made. An apply/API failure can use that snapshot; a post-apply
verification failure preserves it for operator recovery. New guests and non-guest resources have no
automatic inverse, so they remain supervised below A4.

Automated rollback proof lives in the local test suite (`tests/`, run by `bin/check`): an actuator
claims an A4 promotion only when its failure-case rollback is exercised there and recorded live.
Historical rehearsal evidence remains in the journal.

## OpenTofu state today (census 2026-09-26, SKY-025 P12)

These are the inputs to the Phase 15 per-actuator `tofu state mv` split. OpenTofu 1.11.8; providers
bpg/proxmox 0.111.1, cloudflare/cloudflare 5.24.0, kevynb/technitium 0.4.0. One local state file,
`tofu/terraform.tfstate`, PBKDF2 + AES-GCM encrypted; it is git-ignored and **not in git**.

| Stack | Addresses |
|---|---|
| `proxmox-core` | `proxmox_virtual_environment_container.pbs`, `…container.pool_ct["adguard-core"]`, `…container.pool_ct["athena"]` (a pending `moved` block renames it to `core_ct["athena"]` on the next apply), `proxmox_virtual_environment_vm.docker_dmz`, `…vm.ubuntu_2404_base` |
| `proxmox-network` | none: no resource uses `provider = proxmox.network` |
| `technitium-dns` | `technitium_record.aliammar_net[*]` (10 vanity names), `technitium_record.apps_service[*]` (9 app hosts) |
| `cloudflare-dns` | `cloudflare_dns_record.tunnel[*]` (6 public hosts) |

The last recorded plan (`inventory/tofu-drift.txt`, 2026-09-11, untracked) showed 1 add, 1 change, 1 destroy.
The split starts from a freshly reviewed plan, not from an assumed zero.
