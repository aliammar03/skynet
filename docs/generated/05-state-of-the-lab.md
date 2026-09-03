---
title: State of the Lab
generated: 2026-09-04
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-04 03:43 PKT** · The lab is serving normally across every surface this
report-only pass could inspect. Both Proxmox nodes answered, every non-template guest is running,
all 18 observed Docker containers report healthy, every configured TLS endpoint answered, and the
switch plus both access points remain connected.

> [!quote] Agent's log
> This is a healthy night with one timing-shaped yellow flag: the fresh daily backups succeeded,
> but verification has not yet caught up with ten of the new snapshots. Yesterday those same guest
> groups showed verified latest snapshots. That makes this evidence of a verification lag, not of
> broken backups—but recovery confidence stays yellow until the new snapshots turn green.

## Tonight at a glance

| System | State | Evidence from this pass |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | About 62h uptime; this read-only nightly completed from it |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; every non-template guest is running |
| 🐳 DMZ Docker | 🟢 Healthy | 18/18 observed containers are running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains up and healthy |
| 🧱 OPNsense | 🟡 Watch | 39 aliases / 27 rules / 1 reservation; 22 declared hosts live and 4 silent |
| 📡 Network gear | 🟢 Connected | Main switch and both APs are up; 25 client associations observed |
| 🔐 TLS endpoints | 🟢 Reachable | 7/7 configured certificate probes answered |
| 🗄️ PBS datastore | 🟡 Verification pending | 122 snapshots in 20 groups; 11 latest snapshots currently have no verification state |
| 💾 Proxmox backup jobs | 🟢 Last run OK | Core 03:30 and network 02:00 jobs both returned **OK** to `pbs-unraid` today |
| 👁️ Inventory and docs | 🟢 Fresh | Collected and rendered at about 03:43 PKT |

## What changed since `origin/main`

### Eleven fresh backups landed; verification is still catching up

The datastore grew from **111 to 122 snapshots** across the same 20 guest groups. Both scheduled
Proxmox jobs completed successfully today. Ten groups whose latest snapshots were verified in the
baseline now have newer snapshots with no verification state; VM 10015 remains unverified as it was
yesterday. The affected latest snapshots are core CTs 731 and 751; core VMs 10015, 9000, and 9090;
network CTs 525, 635, 730, 750, and 837; and network VM 5001.

The sequence matters: collection ran minutes after the core backup job. A pending verification
state at that point is plausible and does not invalidate the older verified restore points. It is
still an operational gap worth watching, and neither PBS verification nor backup-job success proves
that an end-to-end restore works.

### Service state stayed steady; point-in-time presence shifted

- Proxmox guest identities and power states are unchanged. The Ubuntu base template remains stopped
  by design; every workload guest is running. VM 10015 now has about 26h uptime, with no new reboot
  visible during this comparison window.
- Docker still reports the same 18 containers running and healthy. No workload regression appeared.
- OPNsense configuration counts remain **39 aliases, 27 rules, and 1 reservation**. Declared-host
  presence moved from **24 live / 2 silent** to **22 live / 4 silent**. `10.10.10.60` and
  `10.10.10.65` joined the already-silent `10.10.10.55` and `10.10.80.37`; this is a single
  ARP/ICMP observation, not proof that four services failed.
- Omada still reports all three devices connected. Observed client associations moved from 32 to
  25, while remaining switch PoE budget moved slightly from 107.7 W to 108.1 W.
- Certificate reachability remains 7/7. DNS records, routes, and firewall configuration show no
  substantive change beyond live counters and timestamps.

## Collection gaps and anomalies

`scripts/envsync.sh` again reported that `aiometadata` and `aiostreams` have no host
`project.env`, then exited `1`; no encrypted env file changed. This is an unresolved collection
gap, not evidence that either running service is unhealthy.

No local SSH certificate directory was present under the documented grant path, so no root grant
was active and the root-grant audit was skipped. The four silent declared addresses belong to three
approved admin-client slots (`10.10.10.55`, `.60`, `.65`) and the Authentik identity address
(`10.10.80.37`). Authentik's separate management-plane guest is running; this probe alone cannot
establish whether the identity address is expected to answer continuously.

## Human attention

> [!warning] Worth checking
> - **Verification follow-through:** confirm the ten newly pending PBS snapshots acquire an `ok`
>   state after the scheduled verification cycle; VM 10015 remains the longer-lived gap.
> - **Restore proof:** exercise a real restore. Healthy jobs and verified chunks are ingredients,
>   not an end-to-end recovery demonstration.
> - **Environment backup gap:** decide whether `aiometadata` and `aiostreams` intentionally lack
>   `project.env`, and make envsync's exit behavior match that decision.
> - **Identity presence:** confirm whether `10.10.80.37` should answer continuously before treating
>   its silence as an incident. The three silent admin-client addresses may simply be offline clients.

## Where the build stands

SKY-018 has completed Phase 6 of 12; Phase 7, policy over the OpenTofu plan, remains next. SKY-005,
SKY-006, SKY-008, and SKY-020 remain in flight. The autonomy boundary did not move: this pass
performed read-only collection and wrote reviewable repository artifacts only. It made no guest,
DNS, firewall, service, credential, or privileged-host change.

## Commentary

The important distinction tonight is between **freshness** and **proof**. Eleven successful new
backups are useful; ten verification states temporarily disappearing because “latest” now points at
new material is understandable. But the honest status is still yellow until the verifier catches
up—and still incomplete until a restore drill turns stored data into a working system.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[20-firewall|firewall]] ·
[[40-hosts/server-proxmox-core|core host]] · [[40-hosts/server-proxmox-network|network host]] ·
[[50-network-gear|network gear]] · [[90-backup-status|backup status]]. This narrative is regenerated
by the agent; deterministic pages remain the source views._
