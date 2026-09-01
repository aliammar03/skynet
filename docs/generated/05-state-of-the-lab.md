---
title: State of the Lab
generated: 2026-09-01
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-01 23:51 PKT** · The lab is available and broadly healthy across every surface
this report-only pass could read. Both Proxmox nodes answered, all expected running guests remained
up, all 18 observed Docker containers reported healthy, every certificate endpoint answered, and
all three Omada devices stayed connected.

> [!quote] Agent's log
> The compute and service layer is reassuringly quiet. The one real change is at the firewall:
> several placeholders, transitional clients, and DHCP reservations disappeared since `main`.
> Nothing in Skynet's own leash changed, but a read-only nightly cannot prove who made that edit—so
> this report records it plainly instead of laundering it into “normal telemetry.”

## Tonight at a glance

| System | State | Evidence from this pass |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | Uptime advanced from 4h 22m to 10h 6m; no reboot boundary |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; running/stopped guest identities are unchanged |
| 🐳 DMZ Docker | 🟢 Healthy | 18/18 observed containers are running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains up and healthy |
| 🧱 OPNsense | 🟡 Changed | 39 aliases, 27 rules, 1 reservation; see the configuration delta below |
| 📡 Network gear | 🟢 Connected | Main switch and both APs connected; 30 clients total |
| 🔐 TLS endpoints | 🟢 Reachable | 7/7 configured certificate probes answered |
| 🗄️ PBS (core CT 240) | 🟢 Running | The guest is up; this is availability, not restore proof |
| 💾 Backup proof | ⚪ Unverified | PBS credential absent and no root grant active |
| 👁️ Inventory and docs | 🟢 Fresh | Collected and rendered at about 23:51 PKT |

## What changed since `origin/main`

### A smaller firewall surface

The live read-only OPNsense view fell from **41 → 39 aliases**, **29 → 27 rules**, and **5 → 1
DHCP reservations**:

- Empty placeholders `HOST_SMTP_RELAY` and `ROLE_IOT_ADMIN_TARGETS` were removed, together with
  rules 330 (workstation → IoT administration) and 350 (Authentik mail).
- `ROLE_ADMIN_CLIENTS` dropped the three transitional VLAN 30 addresses and now contains only four
  VLAN 10 clients.
- `ROLE_NFS_CLIENTS` dropped `10.10.20.15` and `10.10.90.15`; it now contains Docker DMZ plus the
  Proxmox-node role.
- Four mobile-device reservations disappeared, leaving only the workstation reservation.
- The self-leash stayed intact: `HOST_SKYNET_OPS` is still `10.10.90.90`,
  `ROLE_OPS_PRIV_TARGETS` is empty, and rules 360–390 remain enabled and unchanged.

This is a meaningful configuration delta, not serializer noise. The nightly observed it but made
no firewall write.

### Ordinary movement elsewhere

- No guest identity or power-state change was observed. The Ubuntu base template remains stopped by
  design; all other listed guests are running.
- Docker container identity, image, state, and health are unchanged. Only ages, counters, and two
  writable-layer sizes moved.
- Omada client count moved from 29 to 30: Ali's AP now reports six clients, Mom's AP five, and the
  switch nineteen. All devices are connected and report no pending upgrade.
- OPNsense presence improved from 23 live / 8 silent to 25 live / 1 silent because the removed
  transitional addresses are no longer in the probe set; `10.10.10.55` is the sole silent target.
- The secondary DNS zone advanced from SOA serial `2026090100` to `2026090101`; no collected zone
  reports expiry, validation, sync, or notification failure.
- `scripts/envsync.sh` found no `project.env` for either tracked project, so no encrypted environment
  file changed.

## Backup and grant truth

Core CT 240 and its TLS endpoint are reachable, but the PBS collector stayed idle because
`/opt/skynet-ops/secrets/pbs.env` is absent. No local `~/.ssh/certs/` directory was present, so no
root grant was active and the root-grant audit harvest was skipped. Snapshot freshness, restic
payloads, restore behavior, and the L5 Google Drive mirror were not verified by this pass.

## Human attention

> [!warning] Worth confirming
> - **Firewall delta:** confirm that removing the two placeholders, two service rules, three role
>   members, and four mobile reservations was intentional. Skynet only observed the live result.
> - **Backup proof:** a running PBS guest and a reachable TLS listener do not prove recent snapshots
>   or successful restoration; run the credentialed verification path when convenient.

## Where the build stands

SKY-018 has completed Phases 1–5 of 12; Phase 6, rollback executors, is next. SKY-005, SKY-006,
and SKY-008 also remain in flight. The autonomy boundary did not move: this pass performed T1
collection and wrote reviewable repository artifacts only. It made no guest, DNS, firewall,
service, credential, or privileged-host change.

## Commentary

The systems that serve the lab look calm; the policy surface is the interesting part tonight.
Shrinking unused firewall scaffolding can be healthy housekeeping, and the unchanged leash is the
most important safety fact. Still, intent belongs to the person or reviewed change that made it,
not to an observer arriving afterward. Until that provenance is confirmed, yellow is the honest
color.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[20-firewall|firewall]] ·
[[40-hosts/server-proxmox-core|core host]] · [[40-hosts/server-proxmox-network|network host]] ·
[[50-network-gear|network gear]] · [[90-backup-status|backup status]]. This narrative is regenerated
by the agent; deterministic pages remain the source views._
