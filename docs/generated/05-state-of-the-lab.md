---
title: State of the Lab
generated: 2026-09-01
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-01, 17:36 PKT** · The lab is available and answering across every source the
report-only pass could inspect. Both Proxmox nodes are online, all 18 Docker containers are
running and healthy, the three managed network devices are connected, and the firewall mirror
remains internally consistent. One event deserves daylight: the ops VM restarted this afternoon.

> [!quote] Agent's log
> The dashboard is mostly green, but the useful story is not “nothing happened.” Skynet's own
> VM crossed a reboot boundary between snapshots. It came back and produced this report; the
> cause was not established by a T1 inventory pass and should not be invented after the fact.

## Tonight at a glance

| System | State | What the evidence says |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟠 Running after restart | About 3.9 hours uptime at collection; previous snapshot showed about 3.9 days |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; guest identities and running/stopped states match `origin/main` |
| 🐳 DMZ Docker | 🟢 Healthy | 18 of 18 containers running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains healthy on `2026.8.2` |
| 🖧 Firewall | 🟢 Steady | 41 aliases, 29 rules, 6 reservations; mirror HEAD `a610af0` |
| 📡 Network gear | 🟢 Connected | Main switch and both APs connected; no upgrade flagged |
| 🗄️ PBS (core CT 240) | 🟢 Running | In `ops-managed`; about 2.2 days uptime |
| 💾 Backup proof | ⚪ Unverified | PBS credential absent and no root grant active |
| 👁️ Inventory and generated docs | 🟢 Fresh | Collected at 17:36 and rendered at 17:39 PKT |

## What changed against `origin/main`

The comparison base is `b3cde47`. Its sources were not all collected at the same moment: Proxmox
at 12:50, Docker and DNS at 03:44, firewall at 17:23, and network gear at 17:28 PKT. Against that
mixed-age baseline:

- **`vm-skynet-ops` restarted.** VMID 9090's uptime fell from 334,857 seconds to 13,894 seconds
  while its state remained `running`. No other guest crossed a restart boundary. Network CT 730
  had already restarted before the baseline and continued accumulating uptime normally.
- Proxmox guest identities, pool membership, and running/stopped states are unchanged. The four
  core VMIDs already absent from recent snapshots—101, 231, 999, and 9091—remain absent.
- Docker reports the same 18 container identities and images, all healthy. Remaining Docker
  differences are live size, uptime, and age presentation.
- Firewall structure is unchanged at 41 aliases, 29 rules, and 6 reservations. The mirrored git
  checkout was at `a610af0`; the collector found no semantic firewall diff from the baseline.
- The Technitium primary zone serial advanced from 286 to 287 and the secondary-zone serial
  rolled to `2026090100`; sync, notify, expiry, and validation failure flags remain clear.
- The network snapshot changed only in live counters: the main switch reported 19 clients instead
  of 18. All three devices remain connected on the same firmware with no upgrade flagged.
- `scripts/envsync.sh` found no `project.env` for either tracked project, so no encrypted env file
  changed.

## Backup truth

Core CT 240 is running and the rendered storage view reports `pbs-unraid` available from both
nodes. Those are availability signals, not recovery evidence. The PBS collector stayed idle
because `/opt/skynet-ops/secrets/pbs.env` is absent. No signed root certificate was present, so
the grant audit and deeper restic inspection were skipped. Recent PBS snapshots and the L5 Google
Drive mirror remain unverified by this run.

## Human attention

> [!warning] Worth checking, not silently fixing
> - Establish whether the `vm-skynet-ops` restart was planned; this pass proves recovery, not cause.
> - Verify recent PBS snapshots and the L5 Google Drive mirror through the credentialed backup
>   procedure when convenient.
> - Confirm that core VMIDs 101, 231, 999, and 9091 were intentionally removed.
> - Resolve ownership of `10.10.100.35` before any destruction of stopped CT 1035.
> - CT 526 remains running and unmapped in DNS/reservations.

## Where the build stands

SKY-005, SKY-006, and SKY-008 remain in flight at Phase 2 of 3. The autonomy boundary did not move:
this pass collected read-only evidence, wrote repository artifacts, and proposed them for review.
It made no guest, DNS, firewall, service, or credential change.

## Commentary

The lab did the important thing after its operator VM restarted: it returned to service and could
reconstruct an honest picture from git plus live reads. That is encouraging resilience evidence,
but not a substitute for knowing why the restart happened. Availability is green; backup proof
and restart causality are still open questions.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[40-hosts/server-proxmox-core|core host]]
· [[40-hosts/server-proxmox-network|network host]] · [[50-network-gear|network gear]] ·
[[90-backup-status|backup status]]. This narrative is regenerated by the agent; deterministic
pages remain the source views._
