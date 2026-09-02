---
title: State of the Lab
generated: 2026-09-03
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---

# Skynet — State of the Lab

**As of 2026-09-03 03:38 PKT** · The lab is serving normally across every surface this
report-only pass could read. Both Proxmox nodes answered, every expected running guest stayed up,
all 18 observed Docker containers were running and healthy, all seven TLS probes answered, and the
switch plus both access points remained connected.

> [!quote] Agent's log
> Tonight has two meaningful fingerprints: the public-app DNS wildcard became nine explicit,
> Terraform-managed records, and LibreSpeed was recreated without changing its pinned image or
> health. The lab looks steady, but two declared addresses did not answer presence probes. That is
> a yellow note—not a verdict—because one is an approved client and the other is a running guest.

## Tonight at a glance

| System | State | Evidence from this pass |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 Running | About 37h 54m uptime; no reboot boundary |
| 🖥️ Proxmox | 🟢 Online | Both nodes answered; guest identities and power states are unchanged |
| 🐳 DMZ Docker | 🟢 Healthy | 18/18 observed containers are running and healthy |
| ☁️ Public tunnel | 🟢 Healthy | `cloudflared` remains up and healthy |
| 🧱 OPNsense | 🟢 Stable config | 39 aliases, 27 rules, 1 reservation; counts unchanged |
| 📡 Network gear | 🟢 Connected | Main switch and both APs connected |
| 🔐 TLS endpoints | 🟢 Reachable | 7/7 configured certificate probes answered |
| 🗄️ PBS (core CT 240) | 🟢 Running | The guest and TLS listener are up; this is not backup proof |
| 💾 Backup proof | ⚪ Unverified | PBS credential absent and no root grant active |
| 👁️ Inventory and docs | 🟢 Fresh | Collected and rendered at about 03:38 PKT |

## What changed since `origin/main`

### Public-app DNS moved from a wildcard to explicit names

The `aliammar.net` forwarder zone replaced `*.aliammar.net A 10.10.100.35` with nine explicit A
records pointing to the same apps front door: `aiometadata`, `aiostreams`, `auth`, `calibre`,
`karakeep`, `marinara`, `obsidian`, `sillytavern`, and `speed`. Each new record is annotated
**“Managed by terraform,”** and the zone serial advanced **12 → 22**. Management-service records
were unchanged.

This narrows the names that resolve to the apps proxy while preserving the observed destinations.
The nightly only read and recorded this state; it did not make the DNS change. The previously noted
`tofu-test.tdns.home.aliammar.net → 192.0.2.1` test record is still present.

### LibreSpeed was recreated and recovered healthy

The LibreSpeed container ID changed from `ee933c4df623` to `983d9d2a2458`, with a creation time of
01:26 PKT tonight. Its image remains `ghcr.io/librespeed/speedtest:6.0.2-alpine`, its Compose
configuration hash is unchanged, and the replacement reported healthy at collection time. The
other 17 container identities and health states were unchanged.

### Stable infrastructure, moving telemetry

- Guest identity and power state are unchanged. The Ubuntu base template remains stopped by
  design; every other listed guest is running.
- OPNsense configuration counts remain **39 aliases / 27 rules / 1 reservation**. Its ARP sample
  moved **41 → 39** neighbours and declared-host presence moved **25 live / 1 no-response → 24 live
  / 2 no-response**.
- The non-responding declared addresses are `10.10.10.55` (a member of `ROLE_ADMIN_CLIENTS`) and
  `10.10.80.37` (Authentik). Authentik's CT 837 is running, so absence from ARP/ICMP is not proof
  that the service is down.
- Omada reports all three devices up. The switch client count moved **20 → 16**, Mom's AP **5 → 6**,
  and Ali's AP stayed at **5**; switch PoE headroom moved **108.2 W → 103.1 W**.
- Certificate reachability remains 7/7. Day counters fell normally; no endpoint crossed a warning
  boundary.

## Collection gaps and anomalies

`scripts/envsync.sh` completed but skipped `aiometadata` and `aiostreams` because neither project
has a host `project.env`; no encrypted environment file changed. The PBS collector stayed idle
because `/opt/skynet-ops/secrets/pbs.env` is absent. No local SSH certificate was present, so no
root grant was active and the root-grant audit harvest was skipped.

The local entity test reported **44 passed / 1 failed**: `vhosts.sql` still expects
`*.aliammar.net` to identify `caddy-apps`, but tonight's inventory contains the new explicit app
records instead. The invariant, budget-frontmatter, and digest checks passed. This nightly did not
rewrite the authored test; the PR may remain red until its vhost expectation follows the reviewed
DNS model.

Snapshot freshness, restic payloads, restore behavior, and the L5 Google Drive mirror therefore
remain unverified. A running backup server is availability evidence, not recovery evidence.

## Human attention

> [!warning] Worth watching
> - **Test expectation:** update the vhost derivation fixture/assertion for the explicit app records;
>   it still requires the removed wildcard.
> - **Presence probes:** check whether Authentik (`10.10.80.37`) remains absent on the next pass;
>   its guest is running, but tonight's ARP and ICMP checks did not see it.
> - **DNS provenance:** confirm the intended lifetime of the Terraform test record at
>   `tofu-test.tdns.home.aliammar.net`.
> - **Environment backup gap:** decide whether `aiometadata` and `aiostreams` intentionally lack
>   `project.env`.
> - **Backup proof:** recent snapshots and an exercised restore remain outside tonight's evidence.

## Where the build stands

SKY-018 has completed Phases 1–5 of 12; Phase 6, rollback executors, remains next. SKY-005,
SKY-006, SKY-008, and SKY-020 remain in flight. The autonomy boundary did not move: this pass
performed T1 collection and wrote reviewable repository artifacts only. It made no guest, DNS,
firewall, service, credential, or privileged-host change.

## Commentary

The move from a wildcard to an explicit public-app list is the strongest signal tonight: the
inventory now shows a smaller, reviewable DNS exposure surface instead of one broad catch-all.
LibreSpeed's fresh container ID is also exactly the kind of operational churn worth recording even
when the service lands green. Nothing here earns a victory lap, but the lab is observable enough to
distinguish configuration change, routine telemetry, and genuine unknowns—which is the point of a
report-only night.

— _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[20-firewall|firewall]] ·
[[40-hosts/server-proxmox-core|core host]] · [[40-hosts/server-proxmox-network|network host]] ·
[[50-network-gear|network gear]] · [[90-backup-status|backup status]]. This narrative is regenerated
by the agent; deterministic pages remain the source views._
