---
title: State of the Lab
generated: 2026-09-02
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-02 03:39 PKT** · The lab is available and broadly healthy across every surface
this report-only pass could read. Both Proxmox nodes answered, every expected running guest stayed
up, all 18 observed Docker containers reported healthy, all seven certificate probes answered,
and the switch plus both access points remained connected.

> [!quote] Agent's log
> Tonight's infrastructure is quiet; DNS is not. A new, explicitly Terraform-managed test record
> appeared in the authoritative zone, while the firewall and workload identities held steady. The
> record uses the documentation-only address `192.0.2.1`, which makes it look deliberate, but a
> read-only observer cannot certify intent. It belongs in the report, not under the rug.

## Tonight at a glance

| System | State | Evidence from this pass |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | Uptime advanced to about 13h 55m; no reboot boundary |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; guest identities and power states are unchanged |
| 🐳 DMZ Docker | 🟢 Healthy | 18/18 observed containers are running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains up and healthy |
| 🧱 OPNsense | 🟢 Stable | 39 aliases, 27 rules, 1 reservation; no configuration-count change |
| 📡 Network gear | 🟢 Connected | Main switch and both APs connected; 30 clients total |
| 🔐 TLS endpoints | 🟢 Reachable | 7/7 configured certificate probes answered |
| 🗄️ PBS (core CT 240) | 🟢 Running | The guest and TLS listener are up; this is not backup proof |
| 💾 Backup proof | ⚪ Unverified | PBS credential absent and no root grant active |
| 👁️ Inventory and docs | 🟢 Fresh | Collected and rendered at about 03:39 PKT |

## What changed since `origin/main`

### A Terraform test record appeared in DNS

The `tdns.home.aliammar.net` primary zone advanced from SOA serial **287 → 291** and now includes
`tofu-test.tdns.home.aliammar.net A 192.0.2.1`, annotated by Technitium as **“Managed by
terraform.”** The associated DNSSEC records were regenerated, and the secondary zone advanced
from serial `2026090101` to `2026090102`. No collected zone reports expiry, validation, sync, or
notification failure.

This is the only clear configuration change visible tonight. The address is from TEST-NET-1 and
is not a routable lab endpoint, but the nightly did not create, modify, or remove the record.

### Stable services, ordinary telemetry

- Guest identity and power state are unchanged. The Ubuntu base template remains stopped by
  design; every other listed guest is running.
- Docker container identity, image, state, and health are unchanged. The diff is limited to age,
  mount ordering, and a small writable-layer size movement.
- OPNsense remains at **39 aliases / 27 rules / 1 reservation**. Declared-host presence remains
  **25 live / 1 no-response**; the ARP table moved from 44 to 41 neighbours.
- The Omada estate still has 30 clients: the switch moved **19 → 20**, Ali's AP **6 → 5**, and
  Mom's AP stayed at 5. All three devices report up.
- Certificate reachability remains 7/7. Day counters fell normally; no endpoint crossed a new
  warning boundary.

## Collection gaps and anomalies

`scripts/envsync.sh` returned nonzero after reporting that the tracked `aiometadata` and
`aiostreams` projects have no host `project.env`; no encrypted environment file changed. The PBS
collector stayed idle because `/opt/skynet-ops/secrets/pbs.env` is absent. No local SSH
certificate was present, so no root grant was active and the root-grant audit harvest was skipped.

Snapshot freshness, restic payloads, restore behavior, and the L5 Google Drive mirror therefore
remain unverified. A running backup server is encouraging availability evidence, not recovery
evidence.

## Human attention

> [!warning] Worth confirming
> - **DNS provenance:** confirm that `tofu-test.tdns.home.aliammar.net → 192.0.2.1` is the intended
>   residue or evidence of the current OpenTofu DNS work, and remove it through the reviewed
>   configuration path when the test is complete.
> - **Environment backup gap:** decide whether `aiometadata` and `aiostreams` intentionally lack
>   `project.env`, or whether envsync is missing expected secret-bearing inputs.
> - **Backup proof:** recent snapshots and an exercised restore remain outside tonight's evidence.

## Where the build stands

SKY-018 has completed Phases 1–5 of 12; Phase 6, rollback executors, is next. SKY-005, SKY-006,
SKY-008, and SKY-020 remain in flight. The autonomy boundary did not move: this pass performed T1
collection and wrote reviewable repository artifacts only. It made no guest, DNS, firewall,
service, credential, or privileged-host change.

## Commentary

The lab's serving surfaces look calm. Tonight's useful signal is that the inventory caught the
OpenTofu-shaped DNS experiment immediately and can show its signed-zone consequences without
pretending to know why it exists. That is exactly what a report-only night should do: separate
health from intent, keep the evidence fresh, and leave the decision with the reviewed workflow.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[20-firewall|firewall]] ·
[[40-hosts/server-proxmox-core|core host]] · [[40-hosts/server-proxmox-network|network host]] ·
[[50-network-gear|network gear]] · [[90-backup-status|backup status]]. This narrative is regenerated
by the agent; deterministic pages remain the source views._
