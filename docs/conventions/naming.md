# Spoke · Naming & addressing

> How things in Skynet are named and addressed — VMIDs, IPs, hostnames, slugs, branches. One
> grammar so a name is predictable and a machine can validate it. Governed by
> [`../conventions.md`](../conventions.md).

Each rule is tagged **[testable]** (a lint gate could assert it mechanically — see the parked
Style-C gate) or **[manual]** (holds by review/judgement).

## Guests — VMID and address

- **VMID = 4 digits = VLAN + last octet.** `[testable]` VM 9090 = VLAN 90 + host .90;
  VM 5001 = VLAN 50 + .1. The VMID and the address encode each other.
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
