---
title: State of the Lab
generated: 2026-08-27
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

**As of 2026-08-27** · foundations long graduated; the ops VM itself is now a NixOS flake
(SKY-007, done), and the lab is mid-build on making infrastructure declarative end-to-end
(SKY-008, OpenTofu).

## The one-glance dashboard

| System | State | Note |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 up | NixOS flake, static 10.10.90.90, running, `ops-managed` |
| 🖧 Routing / OPNsense | 🟢 up | config mirrored to git every change (L2); 41 aliases, 29 rules |
| 🐳 DMZ Docker (`vm-docker-dmz`) | 🟢 up | stacks on the "skynet way", GitOps-reconciled |
| ☁️ cloudflared tunnel (LXC 1033) | 🟢 running | was stopped as of the last render (2026-08-20) — back up now |
| 💾 restic → Google Drive (L3) | 🟢 nightly | witnessed restore ✔ |
| 🗄️ PBS → Google Drive (L5) | 🟡 upload live | off-site guest restore still the standing question |
| 👁️ Visibility (these docs) | 🟢 live | rendered nightly from inventory |
| 🧠 Episodic memory (`journal/`) | 🟢 steady | raw episodes + read-time digest (SKY-006, 2/3) |

## Where we are in the build

The foundation arc (A1–A6) and a long tail of directives since are **done**: convention bedrock
(SKY-009), default-lean context (SKY-010), machine-enforced invariants (SKY-011), Obsidian
LiveSync (SKY-013), the Cloudflare tunnel (SKY-014) — and, most recently, **SKY-007**: the ops VM
itself is now defined as a NixOS flake (impermanence, sops-nix, home-manager, least-priv sudo,
self-provisioning agent key), closed out 2026-08-26. Active work right now is **SKY-008**
(OpenTofu provisioning — VM/CT lifecycle + DNS, phase 1/3 done, phase 2 "throwaway guest" has
uncommitted work in flight on a phase branch as of tonight) plus the still-open SKY-005 (recon/
diagnosis discipline, 2/3) and SKY-006 (episodic memory, 2/3 — this very page is part of that
arc).

> [!tip] What's genuinely solid
> - **Truth lives in git.** Compose, secrets (encrypted), firewall, inventory, and now the ops
>   host definition itself — the lab can be rebuilt from the repo alone.
> - **Backups are real, not aspirational.** L3 has a *witnessed* restore behind it.
> - **The ops brain is declarative.** SKY-007 turned `vm-skynet-ops` into a NixOS flake instead of
>   a hand-tuned VM — the next full rebuild is `nixos-rebuild`, not a runbook of manual steps.

## What changed since the last render (2026-08-20 → tonight)

The deterministic pages hadn't been re-rendered in a week, so this catches seven days of drift,
not one night's:

- **VMID renumber looks complete.** The 2026-08-26 SKY-007 close-out left an open thread —
  "renumber VMID 9091 → 9090 on next boot." Tonight's inventory shows VMID **9090** (`vm-skynet-ops`)
  running and tagged `ops-managed`, VMID **9091** (`vm-skynet-ops-nix`) stopped, and the old
  pre-NixOS VMID **999** also stopped. Reads as done — worth Ali confirming on the node, not just
  in the mirror.
- **cloudflared (LXC 1033) is back running** — was stopped at last observation, healthy now.
- **The OPNsense firewall mirror moved** — these are edits made directly in OPNsense (T3, outside
  this agent's write scope; the mirror is read-only T1), not anything this session did:
  - `HOST_SKYNET_OPS` alias content is now `10.10.90.90, 10.10.90.91` (was `.99, .90`) — the new
    `.91` address lines up with the new 9091 guest.
  - Rule 210 (admin clients → management proxy) now explicitly includes `HOST_SKYNET_OPS` as a
    source — the agent can now reach the mgmt proxy directly. Flagging since it widens reach; not
    acted on.
  - A new `PORT_SMB_NFS` alias (445, 2049) replaces a hardcoded `445` on the Unraid SMB rule,
    which now also covers NFS in its description.
  - New alias `HOST_OMADA` (10.10.50.25) joined `ROLE_ADMIN_TARGETS`.
  - `PORT_WEB`'s description regressed from "Standard web ports: HTTP 80 and HTTPS 443." to the
    generic "Ports for WEB" — looks like an unintentional overwrite, harmless but worth a
    one-line fix.
- **DNS**: routine SOA/serial advances on both zones, nothing anomalous.

## What I'm keeping an eye on

> [!warning] Honest open items
> - **PBS→Drive guest restore is still the standing question.** Upload runs nightly; the off-site
>   *guest* recovery round-trip is the thing to keep proving.
> - **SKY-008 P2 has uncommitted WIP** on `phase/sky-008-p2-throwaway-guest` (a new Ubuntu 24.04
>   template + throwaway-guest Tofu module, plus an access-and-trust doc edit) — stashed clean
>   before this run so the nightly branch stayed uncontaminated; pick it back up next session.
> - The `PORT_WEB` alias description drift above — cosmetic, but flag it to Ali.
> - The live, always-current list of what's in flight is in my [[06-agent-digest|agent digest]].

## Commentary

A quiet week by inventory standards — the last render was seven nights stale, and what it mostly
caught was one real infrastructure event (the NixOS cutover finishing its VMID renumber) plus
routine OPNsense housekeeping done by hand. Nothing broke, nothing drifted in a way that needs
fixing tonight. The interesting thread to pull is SKY-008: once VM/CT lifecycle is Tofu-managed,
the "clone a golden template, harden, restic" runbook stops being an imperative script and starts
being a diff. — _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[90-backup-status]]. Agent orientation:
[[06-agent-digest]]. This narrative is regenerated nightly; the deterministic pages are the truth._
