---
title: State of the Lab
generated: 2026-08-30
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-08-30, 13:47 PKT (fourth pass)** · The lab is broadly steady, with one important
backup-topology change that deserves a human look: the core PBS container is running again, while
the network node no longer reports its former PBS container. This pass observed only; it changed
no guest, service, DNS record, firewall rule, or credential.

> [!quote] Agent's log
> I write this page for humans after the factual render. The tables are the evidence; this is my
> honest interpretation of them. My machine-oriented cold-boot view remains
> [[06-agent-digest|the agent digest]].

## Tonight at a glance

| System | State | What the evidence says |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | In `ops-managed`; the separate Nix test VM 9091 remains stopped |
| 🖧 OPNsense / firewall | 🟢 Steady | 41 aliases, 29 rules, 6 reservations; mirror HEAD `aba7911` from 2026-08-26 |
| 🐳 DMZ Docker | 🟢 Healthy | 18 of 18 containers running and healthy, all at roughly 45 hours uptime |
| ☁️ Public tunnel | 🟢 Running | `cloudflared` is healthy; no image or container-set change |
| 🗄️ Core PBS container (CT 240) | 🟢 Running | Changed from stopped on `main`; about 16 minutes uptime when collected |
| 🗄️ Network PBS container (CT 240) | 🟡 Not reported | Present and running on `main`, absent from this node's current resource list |
| 💾 `pbs-unraid` storage | 🟢 Available | Reported available from both Proxmox nodes; live snapshot counts were not read |
| 👁️ Inventory and generated docs | 🟢 Fresh | Collected and rendered at 13:47 PKT |
| 🔐 Root access | ⚪ Inactive | No active certificate directory; grant-audit harvest correctly skipped |

## What changed against `main`

The comparison base is `main` at `29923b7`. Its last inventory snapshot was collected around
13:26 PKT, so this is a short, roughly twenty-minute observation window.

> [!important] PBS changed shape
> Core-node CT 240 (`lxc-proxmox-backup-server`, `ops-managed`) changed from **stopped** to
> **running** and had 970 seconds of uptime at collection. On the network node, CT 240 was
> **running on `main` but is absent now**. At the same time, the `pbs-unraid` storage endpoint
> changed from `unknown` to `available` on both nodes.

Those facts are consistent with a PBS move or consolidation, but this report cannot establish
that intent. It also cannot certify backup freshness: `/opt/skynet-ops/secrets/pbs.env` is not
present, and live restic/PBS snapshot inspection requires credentials or a root grant. So the
honest status is “promising transition, needs confirmation,” not “backup migration complete.”

Everything else is quiet:

- The Docker workload set is unchanged: 18 containers, all running and healthy. Only collection
  timestamps and nondeterministic mount-display ordering moved.
- The firewall mirror content is unchanged: 41 aliases, 29 rules, and 6 reservations.
- DNS record content is unchanged. Resolver expiry and `lastUsedOn` timestamps advanced; the
  record targeting `10.10.100.35` was queried again at 08:45 UTC.
- Legacy VMID 999 is still running and still unexplained. CT 1035 (`lxc-caddy-dmz`) remains
  stopped; CT 526 (UniFi OS Server) remains running.
- Live CPU, memory, disk, network counters, JSON key ordering, collection timestamps, and rendered
  page timestamps account for the rest of the inventory churn.

## Where the build stands

SKY-008 remains at Phase 2 of 3: OpenTofu can exercise VM/CT lifecycle on both Proxmox nodes;
Phase 3 (DNS records and declarative LXC import) remains open. SKY-005 and SKY-006 also remain at
2 of 3. The newer autonomy and reconciliation directives, SKY-017 and SKY-018, are still ideas,
not active implementation.

The deeper foundation continues to hold: definitions and encrypted configuration live in git;
the ops host is declarative; the nightly is report-only; authored changes remain human-merged;
and tonight's raw facts are appended to `journal/` for later retrieval rather than compressed into
a retrospective lesson.

## Human attention

> [!warning] Worth confirming
> - Was network-node CT 240 deliberately removed or moved, and is core-node CT 240 now the intended
>   sole PBS service?
> - After that is confirmed, verify fresh PBS snapshots and the L5 Google Drive mirror through the
>   credentialed backup procedure; storage availability alone is not backup evidence.
> - VMID 999 remains a running, out-of-pool legacy `vm-skynet-ops` with no recorded disposition.
> - Resolve ownership of `10.10.100.35` before destroying stopped CT 1035; clients are still
>   querying the record and nine published applications depend on the correct proxy target.
> - CT 526 remains running but unmapped in DNS/reservations; SKY-008 P3 and SKY-018 remain the
>   natural homes for that reconciliation work.

## Commentary

This is the first pass today with a genuinely material state change. Seeing the core PBS back up
is encouraging, and seeing its storage available from both nodes is better than yesterday's red
picture. But the simultaneous disappearance of the network PBS means the green light needs an
asterisk until intent and backup freshness are verified. I made no attempt to “help” by starting,
stopping, or probing through root: report-only means the evidence lands first and the operator
decides what the transition means.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[40-hosts/server-proxmox-core|core host]]
· [[40-hosts/server-proxmox-network|network host]] · [[90-backup-status|backup status]]. This
narrative is regenerated by the agent; deterministic pages remain the source views._
