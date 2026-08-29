---
title: State of the Lab
generated: 2026-08-30
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

**As of 2026-08-30** · foundations long graduated; SKY-008 (OpenTofu) has both Proxmox nodes
provisioning VM/CT lifecycle end-to-end (Phase 1+2 done, both nodes), DNS + declarative LXC
import (Phase 3) still to start.

## The one-glance dashboard

| System | State | Note |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 up | NixOS flake, static 10.10.90.90, running, `ops-managed` |
| 🖧 Routing / OPNsense | 🟢 up | config mirrored to git every change (L2); 41 aliases, 29 rules, unchanged since 08-29 |
| 🐳 DMZ Docker (`vm-docker-dmz`) | 🟢 up | all 18 containers healthy, uptimes aging normally (no new restart since the 08-28 event) |
| ☁️ Public tunnel (cloudflared, docker container on `vm-docker-dmz`) | 🟢 running | 10+ days up, untouched |
| 💾 restic → Google Drive (L3) | 🟢 nightly | witnessed restore ✔ |
| 🗄️ PBS (LXC 240, `ops-managed`) | 🔴 **stopped** | 4th night running/rendered stopped since 08-27 — still unconfirmed, still not acted on |
| 🗄️ PBS → Google Drive (L5) | 🟡 at risk | nothing to mirror while PBS itself is stopped |
| 👁️ Visibility (these docs) | 🟢 live | rendered nightly from inventory |
| 🧠 Episodic memory (`journal/`) | 🟢 steady | raw episodes + read-time digest (SKY-006, 2/3) |

## Where we are in the build

SKY-008 (OpenTofu provisioning) is holding at **Phase 1+2 done on both Proxmox nodes**: core has
a permanent clone-source template (`ubuntu-2404-base`, VMID 9000) and a proven clone→destroy
round-trip; the network node has its own provider, its own privilege-separated token, and its own
proven round-trip. **Phase 3** (DNS records + declarative LXC import) hasn't started.

Since the last render, `main` picked up a batch of planning/decision work that hadn't made it
into an inventory narrative yet: **ADR 0005** (full agent control as the terminal goal — autonomy
is earned, reversible, never self-granted), the naming convention spoke finalized (`docs/
conventions/naming.md` grew from a draft to the full grammar), and two new ideas-stage directives
— **SKY-017** (the road to full agent control: verification, proving ground, evidence-earned
ratchet) and **SKY-018** (eight-layer reconciliation: entity spine, the Analyze phase, the
verification toolchain).

Everything else that graduated earlier is holding steady: convention bedrock (SKY-009),
default-lean context (SKY-010), machine-enforced invariants (SKY-011), Obsidian LiveSync
(SKY-013), the Cloudflare tunnel (SKY-014), and SKY-007 (ops VM as a NixOS flake, closed out
2026-08-26). SKY-005 (recon/diagnosis discipline) and SKY-006 (episodic memory) are both sitting
at 2/3.

> [!tip] What's genuinely solid
> - **Truth lives in git.** Compose, secrets (encrypted), firewall, inventory, and the ops host
>   definition itself — the lab can be rebuilt from the repo alone.
> - **VM/CT lifecycle is declarative on both nodes.** Tofu proved clone→boot→destroy on core
>   *and* network — the standalone-node split (separate ACLs, separate VMID spaces) is handled,
>   not assumed away.
> - **The ops brain is declarative.** SKY-007 turned `vm-skynet-ops` into a NixOS flake — the
>   next full rebuild is `nixos-rebuild`, not a runbook of manual steps.

## What changed since the last render

> [!warning] Housekeeping first: two nightly PRs are backlogged
> `main` was 12 commits behind `origin/main` at the start of this run (last inventory merge was
> **#111**, 08-27) — **PR #113** (nightly 08-28) and **PR #115** (nightly 08-29) are still open,
> unmerged. I branched tonight from a freshly fast-forwarded `main`, so this page compares against
> the *actual* last observed state (PR #115's tip, `f9d63d9`) rather than the stale `main` — but
> the generated-doc/inventory diff this PR carries spans all three nights at once, since `main`
> itself hasn't caught up. Nothing broken by this — just flagging that the merge queue is growing;
> worth clearing #113/#115 (report-only, safe to merge) before it gets harder to review.

Comparing against `f9d63d9` (last night's actual output, 2026-08-29 03:30 +05):

- **PBS (VMID 240) is still stopped.** No change from last night — this is now its 4th
  consecutive night stopped (last seen running 08-27). Still nothing in the journal or recent PRs
  that explains it; still not acted on (T2 guest-power action, outside report-only scope). This is
  the one item that's aging into "needs a human decision," not just a flag.
- **The old pre-NixOS `vm-skynet-ops` (VMID 999) is still running.** Same as last night, no new
  information — persisting, not worsening.
- **`vm-docker-dmz`'s mystery restart resolved itself into "just one event."** Every container's
  uptime advanced by exactly ~24h since last night (`Up 11 hours` → `Up 35 hours`) — no second
  restart happened. The ~08-28 16:30 reboot/restart flagged last night stands as a one-time event,
  not a recurring pattern.
- **OPNsense firewall mirror: byte-identical to last night** — 41 aliases, 29 rules, no drift
  (last night's mirror already absorbed the `HOST_SKYNET_OPS`/`PORT_SMB_NFS`/`HOST_OMADA` edits
  from the 08-27→08-29 window).
- **DNS**: routine SOA serial advance only (`tdns.home.aliammar.net` 2026082801 → 2026082901),
  cert `lastUsedOn` timestamps moved, nothing anomalous.
- Docker container inventory: same 18 containers, no adds/removes, routine layer-size churn only.

## What I'm keeping an eye on

> [!warning] Honest open items
> - **PBS (VMID 240) — 4 nights stopped, needs a human call.** This is the item most worth Ali's
>   attention tonight; L5 backup has had nothing to mirror since 08-27.
> - **Two nightly PRs waiting on merge** (#113, #115) — both report-only/generated-only, should be
>   safe to fast-track so `main` stops drifting from reality.
> - **VMID 999 still running, unexplained** — probably benign, still unconfirmed.
> - From the 2026-08-28 entity-model decision, still open: where does `10.10.100.35` actually live
>   now that CT 1035 (caddy-dmz) is stopped and slated for destroy — nine published apps depend on
>   getting this right before that destroy happens. Also open: CT 526 (UniFi controller) is
>   running and unmapped in DNS/reservations (feeds SKY-018 P4), and whether `arcane-manager`
>   becomes a declared GitOps exception or joins the loop.
> - SKY-008 P3 (DNS + declarative LXC import) is the next phase whenever picked back up.
> - The live, always-current list of what's in flight is in my [[06-agent-digest|agent digest]].

## Commentary

A calm night operationally — no new drift, no new surprises. The two open items from last night
(PBS stopped, VMID 999 running) are exactly where they were: neither better nor worse, just
older. The only genuinely new thing worth naming is process, not infrastructure: the nightly PR
queue itself is backing up (two nights unmerged), and `main` is running far enough behind that
"diff against main" and "diff against last night" are no longer the same question — I answered
both above rather than picking one. Nothing here needed nightly to act (report-only, all outside
auto-approve scope regardless), so nothing was touched. — _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[90-backup-status]]. Agent orientation:
[[06-agent-digest]]. This narrative is regenerated nightly; the deterministic pages are the truth._
