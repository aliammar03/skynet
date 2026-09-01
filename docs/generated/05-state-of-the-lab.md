---
title: State of the Lab
generated: 2026-09-01
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-01, evening PKT** · The lab is available and answering across every source the
report-only pass could inspect. Both Proxmox nodes are online, all Docker containers are running and
healthy, the three managed network devices are connected, and the firewall mirror is internally
consistent. Two things earned daylight tonight: the ops VM crossed a reboot boundary this afternoon,
and a review of the generated docs caught a **stale-thread feedback loop** that had been reporting
already-destroyed guests as live.

> [!quote] Agent's log
> The dashboard is green, and this time the useful story is a bug in my own reporting: the cold-boot
> digest was echoing open threads from a journal entry written *before* today's cleanups, and the
> nightly kept copying them forward. Fixed the mechanism, not just the symptom.

## Tonight at a glance

| System | State | What the evidence says |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running (rebuilt) | Uptime reset ~3.9d → ~3.9h — a `nixos-rebuild switch` after merging the P4 collector, not a crash |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; guest identities and running/stopped states match `origin/main` |
| 🐳 DMZ Docker | 🟢 Healthy | All containers running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains healthy |
| 🖧 Firewall | 🟢 Steady | 41 aliases, 29 rules, 6 reservations |
| 📡 Network gear | 🟢 Connected | Main switch + both APs connected on VLAN 50, all static, no upgrade flagged |
| 🗄️ PBS (core CT 240) | 🟢 Running | In `ops-managed` |
| 💾 Backup proof | ⚪ Unverified | PBS credential absent and no root grant active |
| 👁️ Inventory and generated docs | 🟢 Fresh | Collected and rendered this evening |

## What changed against `origin/main`

- **SKY-018 P4 landed.** The Omada network-gear collector is live: `inventory/network-gear.json` +
  `docs/generated/50-network-gear.md` now hold the switch/AP estate (1× ES210GMP, 2× EAP APs), the
  last observed-truth hole in the eight-layer model. Its first run exposed estate drift, which Ali
  reconciled at the source — devices are now static in Omada (switch `.50.3`, Ali's AP `.6`, Mom's AP
  `.7`) and the `ROLE_INFRASTRUCTURE_*` aliases are trimmed to match. Reconciliation is all-green.
- **`vm-skynet-ops` restarted** — expected, from the `nixos-rebuild switch` that materialized the new
  `omada.env` secret. No other guest crossed a restart boundary.
- Proxmox guest identities, pool membership, and running/stopped states are otherwise unchanged.
- Docker reports the same container identities and images, all healthy.
- Firewall structure is unchanged; the mirror now carries `HOST_OMADA` in `ROLE_OPS_API_TARGETS` and
  `8043` in `PORT_OPS_API` (the P4 reachability change) — no semantic drift beyond that.
- `scripts/envsync.sh` found no `project.env` for either tracked project, so no encrypted env changed.

## Backup truth

Core CT 240 is running and the storage view reports `pbs-unraid` available from both nodes — those
are availability signals, not recovery evidence. The PBS collector stayed idle because
`/opt/skynet-ops/secrets/pbs.env` is absent, and no signed root certificate was present, so the grant
audit and deeper restic inspection were skipped. Recent PBS snapshots and the L5 Google Drive mirror
remain unverified by this run.

## Human attention

> [!warning] Worth checking, not silently fixing
> - **OPNsense cleanup (T3):** trim `HOST_SKYNET_OPS` to `10.10.90.90` — it still carries a stale
>   `.90.91` from the pre-SKY-007 9091 ops VM. Optionally drop the `ap-omada-downstairs` reservation
>   now that the AP is static in Omada.
> - **Backup proof:** verify recent PBS snapshots and the L5 Google Drive mirror through the
>   credentialed procedure when convenient — availability is green, recovery is unproven.

## Where the build stands

**SKY-018 is at Phase 4 of 12** — the entity spine, the SQLite join cache, and now the network-gear
collector are all in. P5 (Caddy route + certificate collectors, giving the `vhost` class its source)
is next. SKY-005, SKY-006, and SKY-008 remain in flight. The autonomy boundary did not move: this
pass collected read-only evidence, wrote repository artifacts, and proposed them for review. It made
no guest, DNS, firewall, service, or credential change.

## Commentary

A quiet night on the infrastructure, and a useful one on the reporting: the lab returned cleanly from
its operator-VM rebuild, and the review turned up a real defect in how I remember — a resolved thread
that kept resurrecting because the journal is append-only and nothing taught the digest that a guest
had been destroyed. That's fixed and now gated by a test. Availability is green; backup proof is the
one honest open question.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[40-hosts/server-proxmox-core|core host]]
· [[40-hosts/server-proxmox-network|network host]] · [[50-network-gear|network gear]] ·
[[90-backup-status|backup status]]. This narrative is regenerated by the agent; deterministic
pages remain the source views._
