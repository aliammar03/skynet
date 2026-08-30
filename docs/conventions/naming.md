---
summary: "The one naming grammar — VMIDs, IPs, hostnames, slugs, branches — so a name is predictable and machine-validatable."
tokens: 1760
---

# Spoke · Naming & addressing

> How things in Skynet are named and addressed — VMIDs, IPs, hostnames, slugs, branches. One
> grammar so a name is predictable and a machine can validate it. Governed by
> [`../conventions.md`](../conventions.md).

Each rule is tagged **[testable]** (a lint gate could assert it mechanically — see the parked
Style-C gate) or **[manual]** (holds by review/judgement).

## Guests — VMID and address

- **VMID = VLAN + 2-digit last octet.** `[testable]` The VMID and the address encode each other, so
  either derives the other. **Length varies with the VLAN, not by rule** — 240, 9090 and 10015 are
  all valid — and two forms are in use:
  - **Canonical, use for every new guest:** the VLAN written in full, then the octet.
    `2020` = VLAN 20 + .20 · `5001` = VLAN 50 + .01 · `9090` = VLAN 90 + .90 · `10015` = VLAN 100 + .15.
  - **Legacy, still valid, do not renumber:** the VLAN with its trailing zero dropped.
    `240` = VLAN 20 + .40 · `525` = VLAN 50 + .25 · `635` = VLAN 60 + .35 · `751` = VLAN 70 + .51 ·
    `837` = VLAN 80 + .37 · `1035` = VLAN 100 + .35.
- **Parsing rule** `[testable]`: split the last two digits as the octet, then match the remaining
  prefix against the **declared VLAN set** in both forms. Exactly one match is required. A prefix
  matching none, or both, must be a **declared exception** in `invariants.json` with a `why`.
  (`10xx` is the one genuinely ambiguous prefix — VLAN 10 canonical vs VLAN 100 legacy — which is why
  new guests use the canonical form.)
- **Static addressing is the standard** — see below.
- **Static addressing is the standard — every guest gets a static IP** `[manual]`, configured via
  cloud-init and reserved/excluded in OPNsense so nothing collides. The last octet matches the
  VMID convention above. **DHCP is the exception**, not the rule — the reverse of the pre-2026-08-17
  posture (see ADR [0001](../decisions/0001-static-ip-addressing.md)).
  - *Why:* the fleet is small and long-lived; a predictable address per guest is worth more than
    DHCP's convenience, and it means no guest silently moves. The ops brain (10.10.90.90) is not
    special for *being* static anymore — only for being reserved so it survives a DHCP/OPNsense
    outage and can drive `runbooks/dr/DR-network-node.md`.
- **VM 5001 (OPNsense), CT 635, CT 837, Unraid VM 2020 never join a pool** `[manual]` — visible
  under T1, never touched (T3). This is a blast-radius law, restated here because it rides on the
  addressing scheme.

## Hostnames

- **Lowercase, role-first, hyphenated** `[testable]`: `vm-skynet-ops`, `docker-dmz`,
  `server-proxmox-core`. No uppercase, no underscores, role before qualifier.
- **A hostname is not an identity** `[manual]` — names repeat in the fleet (`lxc-adguard-core` is
  both CT 231 and CT 731). Use the entity ID below wherever something must be referred to uniquely.

## Entity IDs — the one way to name a thing

Every thing the agent reasons about has a stable ID of the form **`<class>/<key>`**. Five classes,
each keyed on a fact that already exists in collected data — nothing is invented, and nothing is
hand-maintained.

| Class | ID form | Example | Address |
|---|---|---|---|
| `node` | `node/<node-name>` | `node/server-proxmox-core` | its own |
| `guest` | **`guest/<role>-<vlan>-<vmid>`** | `guest/docker-dmz-10015` | derived from the VMID |
| `svc` | `svc/<compose-project>` | `svc/karakeep` | **none** — inherits its host guest's |
| `vhost` | `vhost/<hostname>` | `vhost/karakeep.aliammar.net` | the front door's, and it is **not a host** |
| `net` | `net/<device-name>` | `net/ap-omada-downstairs` | its DHCP reservation |

Rules for the guest key `[testable]`:

- **`<role>`** is the guest name minus its `vm-`/`lxc-` prefix. `-core`/`-network` inside a role
  denotes the **Proxmox node**, not the VLAN (`technitium-core` and `technitium-network` are both
  VLAN 70), so it stays part of the role.
- **`<vlan>`** is the slug below. **Omit it when the role already ends with it** — `guest/docker-dmz-10015`,
  never `docker-dmz-dmz-10015`; `guest/skynet-ops-9090`, never `skynet-ops-ops-9090`.
- **`<vmid>`** is last and is the **authoritative key**. The role and VLAN are readable decoration;
  a rename changes them and never changes identity.
- **The ID validates itself** `[testable]`: the VLAN slug and the VMID's prefix encode the same
  fact, so a gate asserts they agree. `guest/anything-dmz-751` fails — 751 is VLAN 70.

### VLAN slugs

| VLAN | Name | Slug | | VLAN | Name | Slug |
|---|---|---|---|---|---|---|
| 10 | Trusted LAN | `lan` | | 60 | Admin Access | `admin` |
| 20 | Servers | `servers` | | 70 | Network Services | `netsvc` |
| 30 | IoT | `iot` | | 80 | Identity | `identity` |
| 50 | Management | `mgmt` | | 90 | Operations | `ops` |
| | | | | 100 | DMZ | `dmz` |

### Edges

`svc —hosted_on→ guest` · `guest —on→ node` · `vhost —fronted_by→ guest|svc —backend→ svc|guest`

- A **vhost's backend is not derivable from its name** `[manual]` — `obsidian.aliammar.net` serves
  `svc/obsidian-livesync`, `speed.aliammar.net` serves `svc/librespeed` — and need not be a service
  at all (`auth.aliammar.net` fronts `guest/authentik-identity-837`). The edge is read from the
  Caddyfile, never inferred.
- **Vhosts come from Caddy, not DNS** `[manual]`. A wildcard record serves many vhosts:
  `*.aliammar.net` covers nine names that have no records of their own.

### Services and addresses

- **A service does not get its own IP** `[manual]`. Its container address is ephemeral and
  bridge-local; its stable position is its **vhost**, or a port published on its host guest.
- **The exception is non-HTTP** `[manual]`: a vhost can only front HTTP. Anything else publishes a
  port on its host guest's IP, or is promoted to a guest of its own with a VMID.

## Slugs & identifiers

- **Directive files:** `SKY-###-kebab-title.md` `[testable]` — zero-padded 3-digit id, then a
  kebab-case title. Minted by `bin/plan`; never hand-numbered.
- **Service directory names:** lowercase, no spaces `[testable]` — `compose/<svc>/` where `<svc>`
  is the compose dir name and the service's identity everywhere (volume paths, `skynet.service`
  label, tag). Short and unqualified: `silly`, `calibre`, `caddy-apps`.
- **Volume role nouns:** a short purpose noun — `data`, `config`, `index`, `db`, `plugins` `[manual]`.
  Don't repeat `<svc>` inside the role (`marinara/data`, not `marinara/marinara-data`). Full rules
  in [`compose.md`](compose.md).
- **ADR files:** `NNNN-kebab-title.md`, 4-digit zero-padded, monotonic `[testable]`. See
  [`docs.md`](docs.md) for the ADR lifecycle.

## Branch names

Branch grammar is a git rule; it lives in [`git.md`](git.md) so all git conventions sit together:
`phase/<name>`, `deploy/<svc>`, `fix/<thing>`, `inventory/<date>`, `plan/<slug>`.
