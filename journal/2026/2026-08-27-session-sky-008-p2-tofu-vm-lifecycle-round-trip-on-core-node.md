---
date: 2026-08-27
kind: session          # session | incident | decision
title: SKY-008 P2 — tofu VM lifecycle round-trip on core node
tier_touched: [T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-008, "docs/design/access-and-trust.md", "server-proxmox-core"]
---

# 2026-08-27 · session · SKY-008 P2 — tofu VM lifecycle round-trip on core node

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Goal: prove the full VM lifecycle with tofu on `server-proxmox-core` (10.10.50.11) — build a
permanent Ubuntu 24.04 base template (VMID 9000) and clone→boot→destroy a throwaway guest (10099)
from declared state. `apply` human-gated, `destroy` a hard checkpoint. API-native cloud-init only.

Decided partway to make the deliverable **permanent**: a base template `ubuntu-2404-base` (9000)
kept as the clone source, rather than a purely throwaway guest. The throwaway (10099) only proved
clone→destroy, then its `.tf` was removed.

The whole run was a chain of Proxmox permission (403) discoveries against the privilege-separated
`svc-tofu@pve!operate` token. Each fix was an out-of-band `pveum` command Ali ran on the node (agent
has no node root; the `!operate` in the token trips zsh history expansion unless single-quoted).

Image handling: the noble cloud image had to be copied into `local`'s `import` store with a
`.qcow2` extension — Proxmox classifies a bare `.img` as ISO and it won't list under the `import`
content type. `cp /var/lib/vz/template/iso/noble-server-cloudimg-amd64.img
/var/lib/vz/import/noble-server-cloudimg-amd64.qcow2`.

Late correction from Ali: **the two Proxmox nodes are NOT clustered.** Standalone → separate `pveum`
DBs, separate VMID spaces, per-node ACLs. This corrected an earlier wrong claim that the `/vms`
binding was cluster-wide; it is core-only. The excluded guests 5001/635/837 live on the *network*
node (untouched by this token); only Unraid 2020 is on core.

Final result: `apply` → 9000 (template=1) + 10099 (running) created; read-API verify (not guest
agent — role lacks VM.GuestAgent.Audit by design); `destroy -target` 10099 → gone, 9000 + docker_dmz
survive; `plan` after removing throwaway.tf = "No changes." Zero drift.

## Actions & outcomes
- `cp` noble img → `local:import/…​.qcow2` → import volume lists (was empty as `.img`)
- apply #1 → 403 `VM.Config.HWType` on /vms/9000 → added to TofuProvisioner role
- apply #2 → 403 `SDN.Use` on /sdn/zones/localnetwork/vmbr0/100 → bound TofuProvisioner at `/sdn/zones/localnetwork` (zone, not per-bridge — provisioning spans VLANs)
- apply #3 → 403 `VM.Config.Options` on /vms/9000 → live role had drifted from doc (missing Options); reconciled full role
- apply #4 → still 403 `VM.Config.Options` → **root cause:** a new VMID isn't a pool member yet at `qmcreate`, so options-class config checks (`Options`/`Cloudinit`/`CDROM`) are evaluated on `/vms/<id>` with NO pool fallback
- decision (Ali) → bind a **config-only** role `TofuVmConfig` at `/vms` (no VM.Allocate/VM.PowerMgmt) so create works for any VMID while destroy/stop stay pool-scoped → 9000 template built (7s)
- clone 10099 → 403 `VM.Config.CDROM` (cloud-init drive is a CDROM) → added to TofuVmConfig
- apply → phantom `+ pool_id` diff on 9000; modify tried to re-add to pool → 500 "already a pool member". Cause: token couldn't read pool membership (`Pool.Audit`), so bpg saw pool_id empty
- fix → `Pool.Audit` **in the TofuProvisioner role** (a token's `/`-level PVEAuditor read does NOT survive the privsep intersection at `/pool/ops-managed`, which already carries a role) → `refresh-only` synced state → apply clean
- verify → 9000 template=1 stopped; 10099 running (cloud-init user `aliammar`, key, 10.10.100.99/24) via `/cluster/resources`
- `tofu destroy -target …sky008_scratch -auto-approve` → 1 destroyed; 9000/docker_dmz intact
- removed `tofu/throwaway-guest.tf`; `plan` = No changes

## Graveyard — tried & abandoned
- **Server-side URL download** (`proxmox_download_file` / `download-url`) → abandoned: needs `Sys.Audit`+`Sys.Modify` on `/` (node-config write, T3). Refused to grant. Image acquisition stays a rare human/root `cp` into `import`.
- **`agent { enabled = true }`** on the resources → abandoned: role has no `VM.GuestAgent.Audit`, so bpg stalls on a 403 waiting for interfaces. Set `enabled = false`; verify running-state via read API.
- **Granting token `PVEAuditor` at `/` to fix pool read** → didn't fix it: the `/`-level read doesn't survive the privsep intersection at `/pool/ops-managed`. `Pool.Audit` had to go in the pool-bound role. (The `/` full-read grant is kept anyway — clean T1.)
- **Binding the full `TofuProvisioner` at `/vms`** (first instinct to unblock create) → rejected: would grant VM.Allocate(destroy)+PowerMgmt over every VM incl OPNsense. Chose the config-only split instead.
- **Per-VMID `/vms/<id>` grants** → considered, not used on core (Ali chose the `/vms` config-only role for zero per-guest friction). Still the recommended approach for the *network* node, to keep 5001/635/837 untouchable.

## Follow-ups / open threads
- **Extend tofu to the network node** (Ali's ask). Standalone node → its own `svc-tofu` + roles + provider endpoint. Keep 5001/635/837 untouchable: **avoid the `/vms` binding there**, use per-VMID grants for any guest it creates. Its own short plan / phase.
- **Golden template `ubuntu-2404-skynet`** (CA trust, principals, onboard-host sshd) is a later cloud-init layer on clones — 9000 is only the base.
- The core `/vms` `TofuVmConfig` role is a real (narrow) blast-radius widening: config-reach over Unraid 2020 on core (name/tags/onboot/cloud-init only, never destroy/stop/disk/NIC). Recorded in access-and-trust + invariants.json + constitution.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
