---
title: State of the Lab
generated: 2026-08-30
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-08-30, 14:01 PKT (fifth pass)** · The lab is steady across this short observation
window. The backup topology seen at 13:47 PKT is unchanged: core-node PBS CT 240 is running,
while the former network-node CT 240 is not present in that node's resource list. This pass was
report-only and made no guest, service, DNS, firewall, or credential change.

> [!quote] Agent's log
> This is the human reading of tonight's evidence. The factual pages remain the source views;
> [[06-agent-digest|the agent digest]] is the separate cold-boot page for operators.

## Tonight at a glance

| System | State | What the evidence says |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | In `ops-managed`; Nix test VM 9091 remains stopped |
| 🖧 OPNsense / firewall | 🟢 Steady | 41 aliases, 29 rules, 6 reservations; mirror HEAD `aba7911` from 2026-08-26 |
| 🐳 DMZ Docker | 🟢 Healthy | 18 of 18 containers running and healthy, all at roughly 46 hours uptime |
| ☁️ Public tunnel | 🟢 Running | `cloudflared` is healthy; image and container set are unchanged |
| 🗄️ Core PBS container (CT 240) | 🟢 Running | Still in `ops-managed`; about 31 minutes uptime when collected |
| 🗄️ Network PBS container (CT 240) | 🟡 Not reported | Still absent from the network node's current resource list |
| 💾 `pbs-unraid` storage | 🟢 Available | Reported available from both Proxmox nodes; snapshot freshness was not inspected |
| 👁️ Inventory and generated docs | 🟢 Fresh | Collected at 14:01 PKT and rendered from that snapshot |
| 🔐 Root access | ⚪ Inactive | No local SSH certificate was present; grant-audit harvest was skipped |

## What changed against `main`

The comparison base is `origin/main` at `48cd2eb`, whose inventory was collected around 13:47
PKT. Across that roughly fourteen-minute interval, **no material configuration or workload-state
change was observed**.

- The Docker workload set remains 18 containers, all running and healthy. Uptime advanced from
  roughly 45 to 46 hours; mount-list ordering changed for a few records without changing mounts.
- Proxmox guest membership and running/stopped states are unchanged. Core CT 240 remains running;
  network-node CT 240 remains absent; legacy VMID 999 remains running.
- Firewall content remains 41 aliases, 29 rules, and 6 reservations at the same mirror commit.
- DNS record content is unchanged. Resolver expiry and `lastUsedOn` values advanced normally.
- The remaining JSON churn is collection time, live CPU/memory/disk/network counters, uptime,
  and API key ordering. Generated-page timestamps advanced with the new snapshot.
- `scripts/envsync.sh` found no `project.env` on the Docker host for any tracked project, so no
  encrypted environment backup changed.

## Backup truth, without wishful thinking

The visible topology is more encouraging than the stopped-core-PBS state reported earlier, but
“running” is not the same as “backups verified.” The PBS collector stayed idle because
`/opt/skynet-ops/secrets/pbs.env` is absent, and this report did not inspect live PBS or restic
snapshots. Confirmation of the intended single-PBS layout and fresh L5 replication remains a
human follow-up, not a green claim this page can honestly make.

## Where the build stands

SKY-008 remains at Phase 2 of 3: OpenTofu lifecycle works on both Proxmox nodes, while DNS records
and declarative LXC import remain open. SKY-005 and SKY-006 also remain at 2 of 3. SKY-017 and
SKY-018 remain ideas. The control model is unchanged: tonight observed, rendered, journaled, and
opened evidence for review; it did not operate the lab.

## Human attention

> [!warning] Still worth confirming
> - Confirm that network-node CT 240 was deliberately removed and core-node CT 240 is now the
>   intended PBS service.
> - Then verify fresh PBS snapshots and the L5 Google Drive mirror with the credentialed backup
>   procedure; storage availability alone is not backup evidence.
> - Decide the disposition of running, out-of-pool legacy VMID 999.
> - Resolve ownership of `10.10.100.35` before destroying stopped CT 1035; published applications
>   still depend on the correct proxy target.
> - CT 526 remains running but unmapped in DNS/reservations.

## Commentary

Quiet is useful when it is measured precisely. This pass does not add another dramatic finding;
it confirms that the topology seen minutes earlier held steady. The yellow asterisk stays on PBS
because the missing credential prevents freshness evidence, not because a new failure appeared.
That distinction matters: the lab looks stable, while the backup claim remains unproven.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[40-hosts/server-proxmox-core|core host]]
· [[40-hosts/server-proxmox-network|network host]] · [[90-backup-status|backup status]]. This
narrative is regenerated by the agent; deterministic pages remain the source views._
