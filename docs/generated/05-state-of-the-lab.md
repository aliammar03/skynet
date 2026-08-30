---
title: State of the Lab
generated: 2026-08-28
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---
> [!quote] Agent's log
> This page is written by me — the operations agent — during the nightly pass, not by the
> deterministic renderer. It's the human-readable read on where Skynet stands: what's healthy,
> what changed, and what I'm keeping an eye on. The tables elsewhere are the truth; this is the
> story that connects them. Regenerated every night; edit the prompt in `runbooks/nightly.md`,
> not this file. (My own cold-boot orientation lives separately in [[06-agent-digest]].)

# Skynet — State of the Lab

**As of 2026-08-28** · foundations long graduated; SKY-008 (OpenTofu provisioning) just cleared
its second of three phases — VM/CT lifecycle is now Tofu-managed on **both** Proxmox nodes.

## The one-glance dashboard

| System | State | Note |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 up | NixOS flake, static 10.10.90.90, running, `ops-managed` |
| 🖧 Routing / OPNsense | 🟢 up | config mirrored to git every change (L2); 41 aliases, 29 rules — unchanged tonight |
| 🐳 DMZ Docker (`vm-docker-dmz`) | 🟢 up | all containers running/healthy, one day older than last night |
| ☁️ cloudflared tunnel (LXC 1033) | 🟢 running | steady since coming back up 2026-08-27 |
| 🛠️ Provisioning (OpenTofu, SKY-008) | 🟢 2/3 phases | VM lifecycle proven on core **and** network node; LXC clone round-trip works |
| 💾 restic → Google Drive (L3) | 🟢 nightly | witnessed restore ✔ |
| 🗄️ PBS → Google Drive (L5) | 🟡 upload live | off-site guest restore still the standing question |
| 👁️ Visibility (these docs) | 🟢 live | rendered nightly from inventory |
| 🧠 Episodic memory (`journal/`) | 🟢 steady | raw episodes + read-time digest (SKY-006, 2/3) |

## Where we are in the build

The foundation arc (A1–A6) and a long tail of directives are **done**: convention bedrock
(SKY-009), default-lean context (SKY-010), machine-enforced invariants (SKY-011), Obsidian
LiveSync (SKY-013), the Cloudflare tunnel (SKY-014), and the ops VM's own NixOS cutover
(SKY-007). The live one is **SKY-008**, and it moved fast overnight: Phase 2 landed for real
(PR #112) — `tofu apply` now proves out a VM lifecycle round-trip on the core node *and* an
extended, standalone deployment on the network node with an LXC clone round-trip. Phase 3 is
scoped but not started: declarative DNS (Technitium) plus a zero-drift LXC *import* (bringing an
existing container under Tofu management without recreating it). SKY-005 (recon/diagnosis
discipline, 2/3) and SKY-006 (episodic memory, 2/3 — this page's arc) round out the open work.

> [!tip] What's genuinely solid
> - **Truth lives in git.** Compose, secrets (encrypted), firewall, inventory, and the ops host
>   definition itself — the lab can be rebuilt from the repo alone.
> - **Provisioning is now declarative on two nodes, not one.** SKY-008 P2 didn't just prove the
>   pattern on core — it extended the same `svc-tofu` + scoped-token shape to the network node,
>   including a working LXC clone. The imperative `provision-vm.md` runbook has a real
>   replacement in progress.
> - **Backups are real, not aspirational.** L3 has a *witnessed* restore behind it.

## What changed since last night (2026-08-27 → tonight)

- **SKY-008 Phase 2 shipped.** PR #112 merged: VM/CT lifecycle proven on both nodes, plus three
  follow-up docs commits that (a) scoped Phase 3 to DNS + LXC import, (b) fixed a read-visibility
  gap where the `/vms` `TofuVmConfig` ACL binding was shadowing node-wide `VM.Audit` — so the
  provisioning token only saw pooled guests until `VM.Audit` was added back — and (c) refreshed
  the core-node DR runbook for the sops-nix secrets model.
- **Inventory itself barely moved.** Tonight's diff is 15 files, but almost all of it is noise,
  not signal:
  - Proxmox core/network JSON: the API returns object keys in a different order every call, so
    the diff *looks* large but no VMID changed state, pool, or tags. The 9090/9091 renumber from
    the SKY-007 cutover is holding steady two nights running.
  - Docker containers: just uptime counters ticking forward a day, still all healthy.
  - DNS: routine SOA serial bumps on both zones.
  - Firewall: only the collection timestamp changed — no new OPNsense edits since last night's
    batch (alias/rule counts identical: 41/29/6).
- **Nothing new broke, nothing new to flag** beyond the two items already open from last night
  (below) — this was a quiet, clean pass end to end.

## What I'm keeping an eye on

> [!warning] Honest open items
> - **PBS→Drive guest restore is still the standing question.** Upload runs nightly; the off-site
>   *guest* recovery round-trip is the thing to keep proving.
> - **`PORT_WEB` alias description is still generic** ("Ports for WEB" instead of the old
>   "Standard web ports: HTTP 80 and HTTPS 443.") — carried over unfixed from 2026-08-27, cosmetic
>   T3 drift, flagging again rather than letting it go stale.
> - **New tonight: JSON key-order churn is worth fixing.** Two nights running, the Proxmox
>   inventory diffs are dominated by non-deterministic key ordering from the API, not real
>   change — it's making the nightly PR noisier to review than it needs to be. Not fixed (not on
>   the auto-approve list), but flagged as a good small follow-up: sort keys before writing in
>   `collect-proxmox.sh`.
> - The live, always-current list of what's in flight is in my [[06-agent-digest|agent digest]].

## Commentary

A genuinely quiet inventory night riding on top of a very productive one before it — SKY-008
went from "phase 2 has uncommitted WIP on a branch" to "phase 2 merged on both nodes" between
last night's render and tonight's. The tofu work is the real story this week; the inventory diff
itself is almost entirely key-shuffling and clock-ticking. If anything's overdue, it's a five-line
fix to make the Proxmox collectors emit stable key order so future nightly diffs are all signal.
— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[90-backup-status]]. Agent orientation:
[[06-agent-digest]]. This narrative is regenerated nightly; the deterministic pages are the truth._
