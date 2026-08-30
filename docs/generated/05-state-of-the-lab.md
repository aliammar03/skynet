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

**As of 2026-08-30 (second pass)** · foundations long graduated; SKY-008 (OpenTofu) has both
Proxmox nodes provisioning VM/CT lifecycle end-to-end (Phase 1+2 done, both nodes), DNS +
declarative LXC import (Phase 3) still to start. The nightly-PR backlog that dominated the last
two nights is **cleared** — `main` tracks reality again.

## The one-glance dashboard

| System | State | Note |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 up | NixOS flake, static 10.10.90.90, running, `ops-managed` |
| 🖧 Routing / OPNsense | 🟢 up | config mirrored to git every change (L2); 41 aliases, 29 rules, mirror HEAD `aba7911` (08-26) — no drift |
| 🐳 DMZ Docker (`vm-docker-dmz`) | 🟢 up | all 18 containers healthy, no restart since the 08-28 one-time event |
| ☁️ Public tunnel (cloudflared, container on `vm-docker-dmz`) | 🟢 running | untouched |
| 💾 restic → Google Drive (L3) | 🟢 nightly | witnessed restore ✔ |
| 🗄️ PBS — network node (CT 240, no pool) | 🟢 up | running |
| 🗄️ PBS — core node (CT 240, `ops-managed`) | 🔴 **stopped** | unchanged since PR #116; last seen running 08-27 — still unconfirmed, still not acted on |
| 🗄️ PBS → Google Drive (L5) | 🟡 at risk | core PBS datastore has had nothing fresh to mirror for days |
| 👁️ Visibility (these docs) | 🟢 live | rendered nightly from inventory |
| 🧠 Episodic memory (`journal/`) | 🟢 steady | raw episodes + read-time digest (SKY-006, 2/3) |

## Where we are in the build

SKY-008 (OpenTofu provisioning) is holding at **Phase 1+2 done on both Proxmox nodes**: core has
a permanent clone-source template (`ubuntu-2404-base`, VMID 9000) and a proven clone→destroy
round-trip; the network node has its own provider, its own privilege-separated token, and its own
proven round-trip. **Phase 3** (DNS records + declarative LXC import) hasn't started.

Everything that graduated earlier is holding steady: convention bedrock (SKY-009), default-lean
context (SKY-010), machine-enforced invariants (SKY-011), Obsidian LiveSync (SKY-013), the
Cloudflare tunnel (SKY-014), and SKY-007 (ops VM as a NixOS flake, closed out 2026-08-26).
SKY-005 (recon/diagnosis discipline) and SKY-006 (episodic memory) are both sitting at 2/3. The
ideas-stage directives from the recent planning batch — **SKY-017** (the road to full agent
control: verification, proving ground, evidence-earned ratchet) and **SKY-018** (eight-layer
reconciliation: entity spine, the Analyze phase, the verification toolchain) — are still ideas,
not started.

> [!tip] What's genuinely solid
> - **Truth lives in git.** Compose, secrets (encrypted), firewall, inventory, and the ops host
>   definition itself — the lab can be rebuilt from the repo alone.
> - **VM/CT lifecycle is declarative on both nodes.** Tofu proved clone→boot→destroy on core
>   *and* network — the standalone-node split (separate ACLs, separate VMID spaces) is handled,
>   not assumed away.
> - **The ops brain is declarative.** SKY-007 turned `vm-skynet-ops` into a NixOS flake — the
>   next full rebuild is `nixos-rebuild`, not a runbook of manual steps.

## What changed since the last render

> [!note] Housekeeping resolved
> The last two narratives opened with a warning that the nightly-PR queue was backing up (#113,
> #115 unmerged, `main` up to 12 commits behind reality). That's **done**: PR #113 (nightly
> 08-28), #115 (nightly 08-29) and #116 (nightly 08-30) all landed on `main`. Local `main` ==
> `origin/main` == `991fa58`, and for the first time in about four nights "diff vs `main`" and
> "diff vs last night" are the same question. This is a second pass on 2026-08-30, run against the
> now-current `main`, so the window it covers is short — a few hours since #116.

Comparing against `991fa58` (PR #116, the morning pass's output):

- **PBS split is worth stating precisely.** There are two containers named
  `lxc-proxmox-backup-server`, one per Proxmox node. The **network**-node one (CT 240, no pool) is
  **running**. The **core**-node one (CT 240, pool `ops-managed`) is **stopped** — and that's the
  one that's been stopped since 2026-08-27. No change tonight. It's not a total backup blackout
  (the network PBS is up), but the core datastore's L5 Drive mirror has had nothing fresh for
  days, and nothing in the journal or recent PRs explains the stop. Still a T2 guest-power action,
  still outside report-only scope — so still just a flag, aging toward "needs a human decision."
- **The legacy `vm-skynet-ops` (VMID 999, no pool) is still running.** Same as the last several
  nights — persisting, not worsening, still unexplained.
- **`vm-docker-dmz`: all 18 containers running, no change.** No adds, no removes, no image
  changes, no new restart. The ~08-28 16:30 event remains a one-off.
- **OPNsense firewall mirror: content byte-identical.** 41 aliases, 29 rules, 6 reservations;
  mirror HEAD still `aba7911` (2026-08-26). Only the collector timestamp moved.
- **DNS**: routine only — the secondary zone's SOA serial advanced `2026082901 → 2026083000` (an
  AXFR refresh), and a few record `lastUsedOn` timestamps moved. One of those is the
  `10.10.100.35` A-record (last queried 2026-08-30 07:50) — a client is still asking for that
  name even though CT 1035 (caddy-dmz) is stopped. That's a query landing, not proof anything
  answers it; it does underline that the `10.10.100.35`-ownership thread needs closing before CT
  1035 is destroyed.
- **Generated docs**: only the `generated:` frontmatter timestamp moved on the factual pages. The
  deterministic machine pages — [[06-agent-digest]] and [[07-context-map]] — regenerated
  **byte-identical** (no ADR / journal / roadmap source change since #116).

## What I'm keeping an eye on

> [!warning] Honest open items
> - **PBS core CT 240 — stopped since 2026-08-27, needs a human call.** Deliberate maintenance or
>   an unplanned stop quietly starving the core instance's L5 mirror. The network PBS being up
>   softens this but doesn't answer it.
> - **VMID 999 still running, unexplained** — probably benign, still unconfirmed.
> - **`10.10.100.35` ownership** (from the 2026-08-28 entity-model decision): where does that
>   address live now that CT 1035 (caddy-dmz) is stopped and slated for destroy? Nine published
>   apps depend on getting this right first — and the record is still being queried.
> - **CT 526 (UniFi controller, network node)** is running and unmapped in DNS/reservations
>   (feeds SKY-018 P4); whether `arcane-manager` becomes a declared GitOps exception or joins the
>   loop is still Ali's call.
> - **SKY-008 P3** (DNS + declarative LXC import) is the next phase whenever it's picked back up.
> - The live, always-current list of what's in flight is in my [[06-agent-digest|agent digest]].

## Commentary

A genuinely quiet pass — and, for once, quiet in a good way. The thing I've spent three
narratives nagging about (the merge queue) is cleared; `main` and reality have converged. With
nothing between the last render and this one but a SOA bump and some metric churn, the honest
report is short: the lab is exactly where #116 left it a few hours ago. The one standing item
that isn't drift is the core-node PBS still being down since the 27th — I want to be careful to
name *which* PBS, because there are two and only one is stopped. Nothing here needed nightly to
act; report-only, all of it outside auto-approve scope regardless, so nothing was touched.
— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[90-backup-status]]. Agent orientation:
[[06-agent-digest]]. This narrative is regenerated nightly; the deterministic pages are the truth._
