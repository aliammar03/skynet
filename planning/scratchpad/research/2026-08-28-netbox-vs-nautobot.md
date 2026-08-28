> Agent-generated research: **do we want a source-of-truth database, and if so which one?**
> Sources cited inline; recency noted where it matters. Skeptical by design — the verdict is
> "not now", and the reasoning for that is the point of the note.

# NetBox vs Nautobot for Skynet

*Compiled 2026-08-28. Current lines: **NetBox 4.6.x** (v4.6.4, 2026-06-30) and **Nautobot 3.x**
(3.0 Dec 2025, 3.1 + commercial app line Apr 2026).*

## 1. What they are, without the marketing

Same ancestry: **Nautobot is a 2021 fork of NetBox** by Network to Code. The DCIM/IPAM core —
sites, devices, prefixes, VLANs, IP addresses, tenancy, custom fields, changelog — is recognisably
the same model in both. They diverged on the *platform* layer above it, not on the data model below.

Both are **Apache 2.0 with an open-core commercial backer**, which is the same risk shape twice:

- **NetBox** — NetBox Labs. Core stays Apache 2.0; confirmed on the record by Jeremy Stretch in the
  "NetBox Community EOL" discussion (2025-10-08) after a scare. But NetBox Labs has explicitly said
  it will license **some add-ons** non-openly to protect commercial investment (Cloud, Enterprise,
  Discovery/Diode, Assurance, the AI assistant). Core open, edges increasingly not.
- **Nautobot** — Network to Code. Same shape: core Apache 2.0, and 3.1 (Apr 2026) launched their
  commercial network-automation apps. Smaller community, more concentrated vendor.

**Myth to kill before comparing:** "NetBox is REST-only, Nautobot has GraphQL." False. NetBox has a
read-only GraphQL API (Strawberry Django; filter syntax changed substantially in 4.3). The real
difference is that Nautobot treats GraphQL as a *primitive* — saved queries reusable from Jobs and
config contexts — not that NetBox lacks it.

## 2. Where they genuinely differ

| | NetBox 4.6 | Nautobot 3.x |
|---|---|---|
| **Automation runner** | Scripts, background jobs, event rules — light, one-off | **Jobs engine**: scheduled, permissioned, chainable, with native **approval workflows** (3.0) |
| **Git as data source** | Plugins/config only | First-class: job code, config contexts, templates, golden-config backups pulled from git repos |
| **Extension model** | Plugins, added later onto a monolithic core | App-first: apps define their own models as deeply as core does |
| **Sync framework** | Per-plugin (Proxbox, LibreNMS, …), Diode/Discovery for ingest | **SSoT framework** — one pattern, many integrations; Device Onboarding now rides it |
| **Flagship apps** | Broad third-party catalog | Golden Config, Device Onboarding (Nornir/Netmiko/NTC-templates), ChatOps, Device Lifecycle |
| **Ecosystem / docs** | Larger by a wide margin, far more homelab material | Smaller, more enterprise-shaped |
| **Data-change review** | Web UI + changelog | Web UI + changelog (+ approval workflows) |

Honest summary: **NetBox is the source of truth; Nautobot is a network-automation platform that
contains one.** If you want the second thing, Nautobot wins outright and it isn't close.

## 3. Fit against *this* lab — where the answer actually comes from

- **DCIM value ≈ zero.** Racks, cables, power feeds, device bays: we have two Proxmox nodes, an
  Unraid box, a firewall appliance and some LXC/VMs. Nothing to model. Half of either product is
  dead weight on day one.
- **IPAM/VLAN value is real but modest**, and already served: OPNsense is authoritative,
  `inventory/firewall/` mirrors it, `docs/generated/10-vlans.md` renders it.
- **Nautobot's headline draw is inapplicable.** Golden Config and Device Onboarding exist to
  template and back up configs across a multi-vendor switch/router fleet over Nornir/Netmiko. Our
  only network device is **OPNsense (VM 5001) — T3, pool-excluded, never touched by the agent**.
  Pointing an automation platform at it is exactly the thing §6 forbids.
- **It inverts our source of truth.** Today: `scripts/collect-*.sh` (T1, read-only) →
  `inventory/*.json` → `docs/generated/`, every change a reviewable diff, PR-gated. NetBox/Nautobot
  move truth into Postgres, and the review surface becomes a web UI changelog. `git diff` stops
  being the artifact a human reads before merge. That collision with §6 ("agent proposes via PR")
  matters more than any feature gap between the two products.
- **Nautobot's Jobs engine is a second automation plane.** Jobs run with the app's own credentials,
  on the app's schedule, outside the PR gate. Approval workflows are in-app, not in git. For a lab
  whose whole safety story is "the leash is version-controlled", that's the sharpest anti-fit in
  this document — and it's Nautobot's main selling point.
- **New standing surface, and it's stateful.** Postgres + Redis + worker(s): `netbox-docker`'s own
  floor is ~4 GB RAM (8 GB for real use); Nautobot with Celery is heavier. Plus a backup obligation
  (PBS + `pg_dump`), a new T2 API token that can write the SoT, and — if we ran Proxbox — Proxmox
  credentials stored inside NetBox's database rather than sops/`0600`, which is a secrets-story
  regression.
- **It doesn't fix the problem we actually have.** Our known inventory defect is *correlation*: a
  reverse-proxy front-door IP reads as a host address (already scoped as **SKY-015**). Neither
  product solves that for free — both would still need the Caddy route table collected first.

## 4. The third option worth knowing about: Infrahub

**OpsMill Infrahub** is the one whose model matches ours: a schema-first graph SoT with real
**branch / diff / merge and CI-style checks in the data layer**, plus `infrahub-sync` for
NetBox/Nautobot migration. Conceptually it's "git semantics for infrastructure data" — which is what
we already do by hand. But it's young, single-vendor, and a heavier stack (graph DB + workers).
Worth watching; not worth adopting for a ~20-guest lab. Note it, don't chase it.

## 5. If we adopt anyway: NetBox, in mirror mode

Not as a source of truth — as a **derived, queryable view**:

- Deploy **NetBox** (not Nautobot: bigger ecosystem, lighter, and we don't want the Jobs plane) via
  `compose/netbox/` under the existing Arcane GitOps loop, image-pinned, on the DMZ Docker host.
- **One-way, git → NetBox.** Collectors keep writing `inventory/*.json`; a small pusher (`pynetbox`,
  or **Proxbox** for the Proxmox half — it syncs clusters, nodes, VMs, LXC and snapshots) reconciles
  NetBox *from* committed truth. Git stays authoritative. NetBox → git only ever as a proposed PR.
- Scoped write token, `0600` under `/opt/skynet-ops/secrets/` (same shape as `cloudflare-dns.env`).
  No plugin gets Proxmox credentials beyond the existing read-only token.
- Stateful → it joins the backup set (PBS snapshot + `pg_dump` into the restic path) and the
  DR runbook, or it's a liability.
- Shape: a **SKY-### idea, long horizon**, T2 (new service + token). Read-only mirror moves no
  blast-radius boundary → no `docs/system-design.md` PR *unless* we ever let it write back.

## 6. Verdict

**Neither, today.** Pick a trigger instead of a preference:

- Lab grows **managed switches/APs with configs worth templating** → revisit, and it's **Nautobot**
  (Golden Config is the whole reason).
- Lab grows enough **guests/prefixes/services that the rendered docs stop scaling** → revisit, and
  it's **NetBox in mirror mode** (§5).
- Neither has happened → **SKY-015** (proxy-aware rendering + canonical host map) buys more accuracy
  per hour than either product, and costs no new service, credential, or backup obligation.

---
### Sources
- NetBox releases (v4.6.4, 2026-06-30) — https://github.com/netbox-community/netbox/releases
- NetBox v4.4 release notes — https://netboxlabs.com/docs/netbox/release-notes/version-4.4
- "NetBox Community EOL" discussion (Stretch, 2025-10-08) — https://github.com/netbox-community/netbox/discussions/20508
- NetBox Labs on add-on licensing — https://netboxlabs.com/blog/expanding-and-sustaining-our-investments-in-netbox-how-were-approaching-licensing-for-some-netbox-add-ons/
- NetBox GraphQL API (Strawberry, read-only) — https://netboxlabs.com/docs/netbox/integrations/graphql-api/
- What's new in Nautobot 3.0 — https://networktocode.com/blog/whats-new-in-nautobot-3-0-2025-12-18/
- Nautobot 3.0 release notes — https://docs.nautobot.com/projects/core/en/stable/release-notes/version-3.0/
- Nautobot Golden Config — https://docs.nautobot.com/projects/golden-config/en/latest/
- Nautobot Device Onboarding (SSoT-based) — https://docs.nautobot.com/projects/device-onboarding/en/latest/user/app_overview/
- Nautobot vs NetBox 2026 comparison (Roger Perkin) — https://www.rogerperkin.co.uk/network-automation/netbox/nautobot-vs-netbox/
- NetBox/Nautobot/Infrahub SoT analysis (Itential) — https://www.itential.com/resource/guide/network-source-of-truth-platforms/
- Proxbox (Proxmox → NetBox) — https://github.com/netdevopsbr/netbox-proxbox
- netbox-docker compose — https://github.com/netbox-community/netbox-docker/blob/release/docker-compose.yml
- Infrahub — https://opsmill.com/blog/introducing-infrahub-beta/ · https://github.com/opsmill/infrahub-sync
