---
date: 2026-08-27
kind: session          # session | incident | decision
title: SKY-008 — tofu extended to network node, LXC clone round-trip
tier_touched: [T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-008, "server-proxmox-network", "docs/design/access-and-trust.md"]
---

# 2026-08-27 · session · SKY-008 — tofu extended to network node, LXC clone round-trip

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Right after core P2 landed (see [[2026-08-27 SKY-008 P2 core]]), Ali said extend tofu to the second
node. Key fact he corrected mid-run: **the two Proxmox nodes are NOT clustered** — standalone, so
separate `pveum` DBs, VMID spaces, per-node ACLs, and a separate tofu provider.

Network node = `server-proxmox-network` @ **10.10.50.10** (core is .11), pinned cert
`proxmox-network.crt` already present. Its `ops-managed` pool was empty (nothing to import), so this
started create/clone-first.

Ali chose to **mirror core exactly, blanket `/vms` config included** — overriding my more-cautious
"avoid /vms on the network node to keep 5001/635/837 untouchable". So on the network node too, tofu's
config-only `/vms` role now reaches OPNsense/Caddy/Authentik (name/tags/onboot/cloud-init/CDROM only,
never destroy/stop/disk/NIC). Recorded in access-and-trust + invariants + constitution.

Token bootstrap: Ali ran the mirror `pveum` block on .10 (roles TofuProvisioner + TofuVmConfig, user,
privsep token, full read, pool/storage/SDN + /vms binds). I sops-encrypted the token to
`secrets/tofu-proxmox-network.env.sops` (binary, same age recipient as core).

Plumbing: second provider alias `proxmox.network` in `tofu/provider.tf`, new vars, `tofu-env.sh`
rewritten to read both tokens + build a combined CA bundle for SSL_CERT_FILE (two self-signed CAs).
Registered the new secret in `nix/modules/secrets.nix`; Ali `nixos-rebuild switch`ed to materialize it.

Lifecycle proof: Ali added the disused **cloudflared LXC (1033)** to ops-managed as a throwaway.
Cloned it via tofu → container **1099**, then destroyed both.

## Actions & outcomes
- `sops --config /dev/null -e --age <recipient> --input-type binary --output-type binary` → `secrets/tofu-proxmox-network.env.sops` (Ali flagged: output-type binary, not json — matches core + sops-nix format=binary)
- added secret to `secrets.nix`; `nixos-rebuild build` failed first: flake can't see untracked file → `git add` the .sops → build OK → Ali `switch`ed → `/run/secrets/tofu-proxmox-network.env` materialized
- `tofu init` (register aliased provider) + `tofu validate` OK; network token authenticates against .10
- wrote `proxmox_virtual_environment_container.netclone_scratch` (provider=network, clone vm_id=1033 → 1099); minimal clone block, `plan` clean (bpg needs no disk/os block for a container clone)
- apply #1 → 500 "Full clone of a running container is only possible from a snapshot" (1033 was running, onboot=1)
- stopped 1033 via API (token has VM.PowerMgmt on pool) → re-apply → 1099 created (79s)
- **destroy checkpoint** (Ali: "destroy them both") → `tofu destroy -target …netclone_scratch` removed 1099; `DELETE /nodes/…/lxc/1033` (out-of-band, not a tofu resource) → vzdestroy task exitstatus OK
- removed `throwaway-net-guest.tf`; `plan` = No changes
- Ali granted the network token full `/` PVEAuditor read (the `--tokens` line he'd hit `!operate` history-expansion on earlier)

## Graveyard — tried & abandoned
- **Full clone of running LXC 1033** → 500; Proxmox requires the source stopped (or clone from a snapshot). Stopped it (throwaway) and cloned offline.
- **Zero-drift IMPORT of the cloudflared LXC** → not attempted to completion: bpg container import tends to drift on `operating_system.template_file_id` (not in a live container's config). Chose the clone lifecycle instead, which needs no clean import.
- **`/`-level PVEAuditor to populate `cluster/resources`** → grant landed (effective perms at / show full read) but `cluster/resources` / `/nodes/<node>/lxc` still return [] for the token. Core happens to also carry `/nodes/<node>` PVEAuditor (leftover from the download_file attempt), which is what populates that listing. Left as-is — cosmetic; tofu reads ops-managed via the pool. A `/nodes/server-proxmox-network` PVEAuditor grant would fix the listing if wanted.
- **Avoiding `/vms` on the network node** (my recommendation to keep 5001/635/837 untouchable) → overridden by Ali ("mirror core"). Config-reach accepted; destroy/stop still blocked.

## Follow-ups / open threads
- **Full node-wide listing** needs `VM.Audit` added to `TofuVmConfig` (the `/vms` binding shadows audit at `/vms/<id>`, so the token lists only pooled guests). `/nodes/<node>` PVEAuditor alone isn't enough. Optional/cosmetic — tofu manages ops-managed via the pool.
- **P3 DNS** (Technitium provider) still open. Network node now has the provider plumbing; ops-managed there is empty again (both throwaways destroyed).
- LXC import (declarative management of an existing container) remains unproven — the bpg `template_file_id` drift is the open question if we want it.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
