---
title: State of the Lab
generated: 2026-09-05
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-05 03:42 PKT** · The lab is serving normally across every surface this
report-only pass could inspect. Both Proxmox nodes answered, every non-template guest is running,
all 18 observed Docker containers report healthy, all seven configured TLS endpoints answered,
and the switch plus both access points remain connected.

> [!quote] Agent's log
> A calm infrastructure night, with one useful milestone and one familiar caveat: Athena has its
> first PBS snapshot, and both scheduled backup jobs finished cleanly. The newest recovery points
> have not yet been verified, though, so “backed up” is ahead of “proven recoverable.”

## Tonight at a glance

| System | State | Evidence from this pass |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | About 86h uptime; this read-only nightly completed from it |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; every non-template guest is running |
| 🐳 DMZ Docker | 🟢 Healthy | 18/18 observed containers are running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains up and healthy |
| 🧱 OPNsense | 🟡 Watch | 40 aliases / 27 rules / 1 reservation; 25 declared hosts live and 2 silent |
| 📡 Network gear | 🟢 Connected | Main switch and both APs are up; 18 switch clients observed |
| 🔐 TLS endpoints | 🟢 Reachable | 7/7 configured certificate probes answered |
| 🗄️ PBS datastore | 🟡 Verification pending | 134 snapshots in 21 groups; 12 latest snapshots have no verification state |
| 💾 Proxmox backup jobs | 🟢 Last run OK | Core 03:30 and network 02:00 jobs both returned **OK** to `pbs-unraid` today |
| 👁️ Inventory and docs | 🟢 Fresh | Collected and rendered at about 03:42 PKT |

## What changed since `origin/main`

### Twelve fresh snapshots landed, including Athena's first

The datastore grew from **122 to 134 snapshots** and from **20 to 21 guest groups**. Eleven
existing guest groups each gained their scheduled daily snapshot, while `lxc-athena` (core CT
10030) appeared in PBS for the first time. Both Proxmox backup jobs report a successful 2026-09-05
run.

Latest-snapshot verification remains pending for the same eleven guests visible in the baseline,
plus the new Athena snapshot. That is consistent with collection occurring minutes after the core
job, but it is still a yellow state: successful creation is not verification, and verification is
not an exercised restore.

### Workloads held steady; point-in-time presence shifted

- Proxmox guest identities and power states are unchanged from `origin/main`. The Ubuntu base
  template remains stopped by design; every workload guest is running.
- Docker reports the identical set of 18 container IDs and images, all running and healthy.
- OPNsense configuration remains **40 aliases, 27 rules, and 1 reservation**. Declared-host
  presence moved from **26 live / 1 silent** to **25 live / 2 silent**: `10.10.80.37`, Authentik's
  identity address, joined the already-silent admin-client slot `10.10.10.55`. This is one ARP/ICMP
  observation, not proof that the identity service is down.
- Omada still reports all three devices connected and on the same firmware. The main switch's
  observed client count moved from 25 to 18; the two AP counts moved from 7/6 to 5/7. Remaining PoE
  budget increased from 106.8 W to 108.2 W.
- TLS reachability remains 7/7. DNS records, published routes, firewall configuration, guest
  membership, container identity, and images show no substantive change.

## Collection gaps and anomalies

`scripts/envsync.sh` again reported that `aiometadata` and `aiostreams` have no host
`project.env`, then exited `1`; no encrypted env file changed. This is an unresolved collection
gap, not evidence that either running service is unhealthy.

No certificate was present under the documented local root-grant path, so no grant was active and
the root-grant audit was skipped. The identity guest (`lxc-authentik`, CT 837) is running, but its
separate `10.10.80.37` service address did not answer this point-in-time presence probe.

## Human attention

> [!warning] Worth checking
> - **Verification follow-through:** confirm the twelve newest PBS snapshots acquire an `ok` state;
>   Athena is newly protected but not yet verified.
> - **Restore proof:** exercise a real restore. Healthy jobs and verified chunks are ingredients,
>   not an end-to-end recovery demonstration.
> - **Environment backup gap:** decide whether `aiometadata` and `aiostreams` intentionally lack
>   `project.env`, and make envsync's exit behavior match that decision.
> - **Identity presence:** confirm whether `10.10.80.37` should answer continuously before treating
>   its silence as an incident. CT 837 itself remains up.

## Where the build stands

The repository advanced substantially between the prior nightly and this pass: SKY-022 completed
its construction-delegation work; SKY-024 is now in progress at Phase 3 of 6; and the deterministic
context map now exposes the new construction-delegation and LXC-provisioning runbooks. SKY-005,
SKY-006, SKY-008, SKY-018, and SKY-020 remain in flight. The autonomy boundary did not move during
this pass: it performed read-only collection and wrote reviewable repository artifacts only. It
made no guest, DNS, firewall, service, credential, or privileged-host change.

## Commentary

Tonight's best news is small but concrete: Athena crossed from “running” to “represented in the
backup estate.” The next honest sentence is just as important: its first snapshot has not yet been
verified. Skynet's health remains green where the probes are direct, yellow where recovery evidence
is incomplete, and deliberately undecided where a single presence sample cannot support a verdict.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[20-firewall|firewall]] ·
[[40-hosts/server-proxmox-core|core host]] · [[40-hosts/server-proxmox-network|network host]] ·
[[50-network-gear|network gear]] · [[90-backup-status|backup status]]. This narrative is regenerated
by the agent; deterministic pages remain the source views._
