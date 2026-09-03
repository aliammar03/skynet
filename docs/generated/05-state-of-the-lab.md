---
title: State of the Lab
generated: 2026-09-03
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-03 11:44 PKT** · The lab is serving normally across every surface this
report-only pass could read. Both Proxmox nodes answered, every non-template guest is running,
all 18 observed Docker containers report healthy, all seven TLS probes answered, and the switch
plus both access points remain connected.

> [!quote] Agent's log
> The broad picture is green, but not perfectly still: the Docker VM crossed a reboot boundary,
> one declared identity host stopped answering presence checks, and DNS moved from a wildcard
> front door to explicit application records in the human-facing render. None of those is a reason
> to reach for a wrench during a report-only run; all three are reasons to leave good evidence.

## Tonight at a glance

| System | State | Evidence from this pass |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | About 46h uptime; the read-only nightly completed from this host |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; guest identities and power states are unchanged |
| 🐳 DMZ Docker | 🟢 Healthy | 18/18 observed containers are running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains up and healthy |
| 🧱 OPNsense | 🟡 Watch | Configuration counts remain 39 aliases / 27 rules / 1 reservation; declared presence is 24 live / 2 silent |
| 📡 Network gear | 🟢 Connected | Main switch and both APs are up; 28 clients observed |
| 🔐 TLS endpoints | 🟢 Reachable | 7/7 configured certificate probes answered |
| 🗄️ PBS datastore | 🟢 Visible | `unraid` reports 111 snapshots in 20 groups; 11 groups have no verification state |
| 💾 Proxmox backup jobs | 🟢 Last run OK | Core 03:30 and network 02:00 jobs both last returned **OK** to `pbs-unraid` |
| 👁️ Inventory and docs | 🟢 Fresh | Collected and rendered at about 11:44 PKT |

## What changed since `origin/main`

### The Docker VM restarted; its workloads recovered

`vm-docker-dmz` (VMID 10015) now reports roughly **10h 40m** uptime, down from about **4d 16h**
in the prior inventory, so it crossed a reboot boundary. Container names and images are unchanged,
and all 18 containers are running and healthy. LibreSpeed also reports about ten hours of age,
consistent with recreation after that boundary. The inventory does not establish why the VM
restarted.

### One declared host changed from present to silent

OPNsense still exposes **39 aliases, 27 rules, and 1 reservation**. Its live table moved from
**25 live / 1 silent** to **24 live / 2 silent**, and `10.10.80.37` changed from ARP-present to
`no-arp,no-icmp`. ARP neighbours fell from 41 to 39. This is a point-in-time reachability signal,
not proof that the underlying service is failed.

### DNS now renders the explicit application front doors

The collected A-record set is unchanged from the latest inventory on `origin/main`, but the
generated service page had not yet caught up with it. Tonight's render replaces the old
`*.aliammar.net` row with nine explicit app records (`aiometadata`, `aiostreams`, `auth`,
`calibre`, `karakeep`, `marinara`, `obsidian`, `sillytavern`, and `speed`), all targeting
`10.10.100.35` and marked **Managed by terraform**. The earlier `tofu-test` record is absent from
both the baseline and tonight's live record set. The `aliammar.net` forwarder serial advanced
**12 → 22** and the secondary serial advanced **2026090102 → 2026090300**; no collected zone
reports expiry, validation, sync, or notification failure.

### Stable services, ordinary telemetry

- Guest identities and power states are unchanged. The Ubuntu base template remains stopped by
  design; every other listed guest is running.
- Omada still reports all three devices connected. Observed clients moved **30 → 28**: the switch
  stayed at 20 while each AP moved **5 → 4**. Remaining PoE budget moved **108.2 W → 107.6 W**.
- Certificate reachability remains 7/7. Day counters fell normally; no endpoint crossed a new
  warning boundary.
- PBS remains at 111 snapshots across 20 groups. Eleven groups currently carry no verification
  state; snapshot existence is not restore proof.

## Collection gaps and anomalies

`scripts/envsync.sh` exited **1** after reporting that `aiometadata` and `aiostreams` have no host
`project.env`; no `.env.sops` file changed. No local SSH host certificate was present, so no root
grant was active and the root-grant audit was correctly skipped.

The PBS API is readable tonight, but payload-level restic freshness, an exercised restore, and the
L5 Google Drive mirror remain outside this pass. A populated snapshot catalog and successful
vzdump tasks are useful evidence; they are not recovery proof.

## Human attention

> [!warning] Worth checking
> - **Docker reboot provenance:** confirm whether VMID 10015's restart was planned; workloads have
>   recovered and are healthy now.
> - **Identity reachability:** check `10.10.80.37` if it is expected to be continuously available;
>   it did not answer ARP or ICMP during collection.
> - **Environment backup gap:** decide whether `aiometadata` and `aiostreams` intentionally lack
>   `project.env`, or whether envsync is missing expected secret-bearing inputs.
> - **Recovery evidence:** schedule a restore exercise and verify the restic/L5 mirror paths; 11
>   PBS groups also lack a current verification state.

## Where the build stands

SKY-018 has completed Phases 1–5 of 12; Phase 6, rollback executors, is next. SKY-005, SKY-006,
SKY-008, and SKY-020 remain in flight. The autonomy boundary did not move: this pass performed T1
collection and wrote reviewable repository artifacts only. It made no guest, DNS, firewall,
service, credential, or privileged-host change.

## Commentary

This is a healthy lab with three honest footnotes, not a flawless green wall. The best news is
operational: the Docker host came back with its whole observed workload healthy, the backup catalog
is visible, and every management surface answered. The best next move is equally plain—explain the
reboot, identify the silent host, and turn "backups exist" into "a restore worked."

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[20-firewall|firewall]] ·
[[40-hosts/server-proxmox-core|core host]] · [[40-hosts/server-proxmox-network|network host]] ·
[[50-network-gear|network gear]] · [[90-backup-status|backup status]]. This narrative is regenerated
by the agent; deterministic pages remain the source views._
