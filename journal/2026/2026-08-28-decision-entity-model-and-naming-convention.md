---
date: 2026-08-28
kind: decision
title: Entity model (five classes) and the final naming convention
tier_touched: [T1]
grants: []
refs: [SKY-018, SKY-017, ADR 0003, ADR 0005, PR #114, docs/conventions/naming.md]
---

# 2026-08-28 · decision · Entity model (five classes) and the final naming convention

## What happened

Started as "NetBox vs Nautobot", ended as the L0 identity layer. Chain: neither product fits (git
stays the SoT) → the real defect is that every generated view joins on **IP**, not on a key → ADR
0001's VMID convention already *is* a key and nothing reads it.

Derivation run against live inventory, no authored mapping: **14 of 19 guests matched** a known
alias/DNS name (240→`HOST_PBS`, 635→`HOST_PROXY_ADMIN`, 751→`tdns-core`, 1035→`HOST_PROXY_APPS`,
10015→`HOST_DOCKER_DMZ`, …), **4 unmatched and stopped** (101 `debian`, 231 + 720 retired AdGuards,
999 the pre-NixOS ops brain), **1 unmatched and running** — CT 526 `lxc-unifi-os-server`, live with
no alias, no DNS record and no DHCP reservation, invisible to every generated view.

Ali asked whether L0 covered docker services too. It didn't. Checked: every container carries
`com.docker.compose.project`, and **10 of 11 running projects match a `compose/` directory by name**.
The 11th is `arcane-manager` — Arcane itself, running on the DMZ host with no `compose/` dir, i.e.
deployed outside the GitOps loop it enforces for everything else. Same hole shape as CT 526, one
layer up. Model widened to five classes.

Naming picked interactively. Ali chose `guest/role-vlan-vmid`. Putting a VLAN word in every ID forced
the vocabulary question, which surfaced that `render-docs.sh`'s `vlan_name()` had **10 and 60
swapped** — 10 rendered as "Admin", 60 as "Trusted LAN". OPNsense's own alias text says *"VLAN 30
members are transitional and should move to Trusted VLAN 10"*, and VLAN 10 holds a workstation, an
iPhone and an iPad while VLAN 60 holds only the Management Caddy front door. The collected firewall
mirror was right; the hardcoded map in the renderer was wrong, and `docs/generated/` had been
publishing it. Ali also flagged VLAN 30 (IoT) missing from the map entirely despite holding 3 hosts,
and `netsvc` over `dns` for 70.

Ali corrected "karakeep's vhost is karakeep.aliammar.net". Checked: **no `karakeep` A record exists** —
it resolves through the single `*.aliammar.net` wildcard. DNS knows one name; the apps Caddyfile
declares nine. So the vhost class cannot be derived from DNS at all.

Writing the convention into `docs/conventions/naming.md` then contradicted the spoke's own
"VMID = 4 digits" rule: 240 is 3, 10015 is 5, and the fleet actually runs **two forms** —
VLAN-in-full (2020, 5001, 9090, 10015) and VLAN-with-trailing-zero-dropped (240, 525, 635, 751, 837,
1035). `10xx` is genuinely ambiguous between them.

## Actions & outcomes
- Derivation audit across `inventory/proxmox-*.json` → 14 matched / 4 stale / 1 running-unmapped (CT 526).
- Compose project ↔ `compose/` dir cross-check → 10 declared / 1 undeclared (`arcane-manager`).
- `render-docs.sh` VLAN map corrected (10↔60 swap, 20, 50, 70 wording) + VLAN 30 named IoT → re-rendered; diff was names and timestamps only.
- Caddyfile read → 9 site blocks; 3 of 9 vhost names don't match their project (`obsidian`→`obsidian-livesync`, `sillytavern`→`silly`, `speed`→`librespeed`); `auth` backends a **guest** (837), not a service.
- Convention landed in `docs/conventions/naming.md`; hub row updated; the "VMID = 4 digits" rule replaced with the two-form parse.
- CT 1035 `lxc-caddy-dmz` confirmed by Ali as stale, to be destroyed.

## Graveyard — tried & abandoned
- **NetBox / Nautobot as the SoT** → abandoned: a fourth home for identity in a system whose defect is un-joined truth; state outside git breaks the rebuild law.
- **Infrahub** → right model (branch/diff/merge in the data layer), abandoned as too young and too heavy for ~20 guests.
- **Ansible inventory as the authored spine** → abandoned: duplicates facts already collected or derivable, and hand-maintained inventories drift. Its *dynamic* Proxmox inventory stays available later as a view.
- **Terratest for the proving ground** → abandoned: Go to assert what `collect-*.sh` already reports.
- **Temporal / durable-execution engine** → abandoned: workflow history is system-class state in its own database.
- **Switching compose to Komodo for rollback** → abandoned in favour of a health-gated wrapper; no platform churn.
- **Name-keyed entity IDs** → abandoned: `lxc-adguard-core` is both 231 and 731, `vm-skynet-ops` both 999 and 9090.
- **`dns` as VLAN 70's slug** → abandoned for `netsvc` (Ali).

## Follow-ups / open threads
- **Where does `10.10.100.35` live now?** `*.aliammar.net` fronts there, `caddy-apps` runs on `.15`, CT 1035 is stopped and slated for destroy. Must be established before the destroy or nine published apps break.
- CT 526 (UniFi controller): running and unmapped — needs an alias/reservation, and is the reason SKY-018 P4 exists.
- `arcane-manager`: declare as an exception with a `why`, or bring it into the GitOps loop. Ali's call; SKY-018 P2's gate forces it.
- VMID form: new guests use VLAN-in-full. The ambiguous `10xx` prefix clears once 1033 and 1035 are retired.
