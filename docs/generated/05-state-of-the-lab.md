---
title: State of the Lab
generated: 2026-09-03
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-03 12:07 PKT** · The lab is serving normally across every surface this
report-only pass could read. Both Proxmox nodes answered, every non-template guest is running,
all 18 observed Docker containers report healthy, all seven TLS probes answered, and the switch
plus both access points remain connected.

> [!quote] Agent's log
> Tonight's clearest change is exactly the kind worth celebrating carefully: PBS now reports a
> successful verification state for ten guest groups that were unverified in the baseline. One
> group—VM 10015—still lacks verification, and a verified snapshot catalog still does not replace
> an exercised restore. The lab looks healthy; its recovery evidence is getting meaningfully better.

## Tonight at a glance

| System | State | Evidence from this pass |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | About 46h uptime; this read-only nightly completed from it |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; guest identities and power states are unchanged |
| 🐳 DMZ Docker | 🟢 Healthy | 18/18 observed containers are running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains up and healthy |
| 🧱 OPNsense | 🟡 Watch | 39 aliases / 27 rules / 1 reservation; 24 declared hosts live and 2 silent |
| 📡 Network gear | 🟢 Connected | Main switch and both APs are up; 32 client associations observed |
| 🔐 TLS endpoints | 🟢 Reachable | 7/7 configured certificate probes answered |
| 🗄️ PBS datastore | 🟡 Nearly verified | 111 snapshots in 20 groups; only VM 10015 has no latest verification state |
| 💾 Proxmox backup jobs | 🟢 Last run OK | Core 03:30 and network 02:00 jobs both last returned **OK** to `pbs-unraid` |
| 👁️ Inventory and docs | 🟢 Fresh | Collected and rendered at about 12:07 PKT |

## What changed since `origin/main`

### Ten more PBS groups now carry verification evidence

The datastore still contains **111 snapshots across 20 guest groups**, with unchanged capacity
figures. The important movement is in verification metadata: unverified latest snapshots fell
from **11 groups to 1**. Core CTs 731 and 751; core VMs 9000 and 9090; network CTs 525, 635, 730,
750, and 837; and network VM 5001 now report `ok`. **Core VM 10015 remains unverified.**

This is stronger evidence that the stored backup data is internally sound. It is not evidence that
a restore has completed successfully, and the payload-level restic and L5 Google Drive mirror paths
remain outside this pass.

### Service state stayed steady while point-in-time telemetry moved

- Proxmox guest identities and power states are unchanged. The Ubuntu base template remains stopped
  by design; every non-template guest is running. VM 10015 has roughly 11h uptime, consistent with
  the reboot boundary already visible in the baseline.
- Docker still reports the same 18 containers running and healthy; no workload regression appeared.
- OPNsense configuration counts remain **39 aliases, 27 rules, and 1 reservation**. Declared-host
  presence remains **24 live / 2 silent**. The ARP table moved from 39 to 37 entries, and
  `10.10.100.65` was reached by ICMP rather than ARP; those are point-in-time observations, not
  configuration changes.
- Omada still reports all three devices connected. Switch client associations moved **20 → 24**;
  both APs remain at 4, for 32 observed associations in total. Remaining PoE budget moved slightly
  from **107.6 W → 107.7 W**.
- Certificate reachability remains 7/7. DNS, routes, firewall configuration, and backup job results
  show no substantive state change beyond live timestamps and counters.

## Collection gaps and anomalies

`scripts/envsync.sh` reported that `aiometadata` and `aiostreams` have no host `project.env`; no
`.env.sops` file changed. This is the same unresolved gap recorded by the earlier nightly.

No local SSH host certificate was present under the documented grant path, so no root grant was
active and the root-grant audit was correctly skipped. `10.10.10.55` and `10.10.80.37` remained
silent to both ARP and ICMP during collection; that is a presence signal, not proof of service
failure.

## Human attention

> [!warning] Worth checking
> - **Restore proof:** run an actual restore exercise; PBS verification is welcome but does not prove
>   the recovery procedure end to end.
> - **Last PBS gap:** investigate or await verification for VM 10015's latest snapshot.
> - **Environment backup gap:** decide whether `aiometadata` and `aiostreams` intentionally lack
>   `project.env`, or whether envsync is missing expected secret-bearing inputs.
> - **Silent hosts:** confirm whether `10.10.10.55` and `10.10.80.37` are expected to answer
>   continuously before treating their absence as an incident.

## Where the build stands

SKY-018 has completed Phase 6 of 12; Phase 7, policy over the OpenTofu plan, is next. SKY-005,
SKY-006, SKY-008, and SKY-020 remain in flight. The autonomy boundary did not move: this pass
performed T1 collection and wrote reviewable repository artifacts only. It made no guest, DNS,
firewall, service, credential, or privileged-host change.

## Commentary

The lab is stable, and tonight's evidence improved in a place that matters. Moving ten backup
groups from “present but unverified” to “verified” is not cosmetic greening; it narrows a real
recovery uncertainty. The remaining discipline is to keep the language honest: VM 10015 is still
unverified, and no collection report can substitute for watching a restore actually work.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[20-firewall|firewall]] ·
[[40-hosts/server-proxmox-core|core host]] · [[40-hosts/server-proxmox-network|network host]] ·
[[50-network-gear|network gear]] · [[90-backup-status|backup status]]. This narrative is regenerated
by the agent; deterministic pages remain the source views._
