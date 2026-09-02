---
summary: "Where Skynet sits, how it's addressed on VLAN 90, and the firewall rules bounding its reach to exactly what it needs."
tokens: 1729
---

# Spoke · Network & placement

> Where Skynet sits, how it's addressed, and the firewall rules that let it reach exactly what it
> needs and nothing more. Governed by [`../system-design.md`](../system-design.md). Sourced from
> plan §1 (placement) and §3 (firewall).

## Placement & VM spec

| Item | Value |
|---|---|
| VMID | **9090** (4-digit convention: VLAN 90 + .90) |
| Name / node | `vm-skynet-ops` on `server-proxmox-core` |
| Network | `vmbr0` tag 90, Proxmox guest firewall enabled |
| IP | **10.10.90.90 static** — deliberate convention exception (see below) |
| OS | **NixOS 26.05** — declarative flake ([`nix/`](../../nix/)) |
| Resources | 4 vCPU · 6 GB RAM · 60 GB disk |
| Base tools | Nix-owned toolchain (`git gh jq curl rsync age sops restic rclone docker node python3`); agent CLIs via home-manager |

**Why the static IP** (ADR [0001](../decisions/0001-static-ip-addressing.md)): static addressing
is the standard for every guest (last octet = VMID convention), so the ops brain is static like
the rest. It is special only in that its reservation is load-bearing — the ops brain must keep its
address when DHCP, i.e. OPNsense, is the very thing that died. It is reserved/excluded in OPNsense
so nothing collides, lives in `ROLE_ADMIN_TARGETS`, and exists so Skynet can drive
`DR-network-node.md` during a routing outage.

## Firewall

VLAN 90 sits in `NET_WEB_EGRESS` (GitHub, model APIs, Google Drive, registries — all over 443).
Consequence: **git over HTTPS + a fine-grained PAT** (GitHub SSH on 22 is blocked, and HTTPS is
friendlier for a git beginner anyway).

### Aliases

| Alias | Type | Members |
|---|---|---|
| `HOST_SKYNET_OPS` | Host | 10.10.90.90 |
| `ROLE_OPS_SSH_TARGETS` | Host | 10.10.100.15; **every onboarded workload host joins here** |
| `ROLE_OPS_API_TARGETS` | Host | 10.10.50.10, 10.10.50.11, 10.10.20.40, 10.10.70.50, 10.10.70.51, + Arcane host |
| `ROLE_OPS_PRIV_TARGETS` | Host | **empty (dormant)** — the T3 slot |
| `PORT_OPS_API` | Port | 8006, 8007, 53443, 3552 |

### Rules (services category, before 700)

| Seq | Action | Source → Destination : service | Purpose |
|---|---|---|---|
| 360 | Pass TCP | `HOST_SKYNET_OPS` → `ROLE_OPS_API_TARGETS` : `PORT_OPS_API` | Proxmox, PBS, Technitium, Arcane APIs |
| 370 | Pass TCP | `HOST_SKYNET_OPS` → `ROLE_OPS_SSH_TARGETS` : 22 | Workload SSH — carries **both** `svc-ops` and granted-root sessions |
| 380 | Pass TCP | `HOST_SKYNET_OPS` → `ROLE_OPS_PRIV_TARGETS` : `PORT_ADMIN_PROXY` | **Dormant** — temporary T3 grants |

**Root grants need no firewall action** — same port 22, same targets; elevation happens in the
SSH layer, not the network layer (see [access-and-trust](access-and-trust.md)). Ali's own access
rides existing rules 220/230 via `ROLE_ADMIN_TARGETS`. Guest firewall on VM 9090: default-deny in,
TCP 22 from the two workstation/admin hosts only.

## DNS resolvers — who may resolve, through whom

Every segment resolves through an **approved resolver only**; the firewall drops DNS (`:53`/`853`)
to anything else (`CORE — Clients → block other DNS`). A service pointed at the wrong resolver fails
to resolve at runtime — and *silently*, because a dropped query looks like a dead server, not a
policy block.

| Alias / host | Members | Role |
|---|---|---|
| `ROLE_DNS_RESOLVERS` | **Technitium** `10.10.70.50` + `.51` (VLAN 70 — split-horizon: resolves the public world **and** the internal `aliammar.net` zone), plus `10.10.70.30`/`.31` | the approved **internal** resolvers |
| `ROLE_DNS_UPSTREAMS` | `1.1.1.1`, `8.8.8.8`, `9.9.9.9` | approved **public** resolvers (reachable from any segment) |
| AdGuard | `10.10.20.30` (`adguard-network`), `10.10.20.31` (`adguard-core`) — VLAN 20 | **not** an approved cross-segment resolver — do **not** point services here (they'll be firewall-dropped) |

- **Default:** internal services use **Technitium** (`10.10.70.50/.51`) — it answers both the public
  world and the internal split-horizon zone. This is the compose template's default `dns:`.
- **Exception — the Cloudflare Tunnel:** `compose/cloudflared` uses the approved **public** upstreams
  (`1.1.1.1`/`8.8.8.8`), not Technitium. It only ever resolves Cloudflare's public edge, and
  Technitium returns an *empty* answer for that edge's `_v2-origintunneld._tcp.argotunnel.com` SRV
  (it serves other SRVs and the legacy `_origintunneld` fine — the newer record is the gap).

## The blast-radius boundary, at the network layer

`ROLE_OPS_SSH_TARGETS` is the SSH half of the write blast radius (the pool set is the Proxmox
half — see [access-and-trust](access-and-trust.md)). A host is reachable for operate/grant work
**only** once it's in this alias. Adding a host here is part of the "new managed host" extension
point in the constitution.

## The apps-ingress rails (realized — SKY-003)

The reverse-proxy edge is no longer hypothetical: the firewall was already staged for it, and
directive [SKY-003](../../planning/projects/SKY-003-apps-reverse-proxy-authentik-sso-ingress.md)
lands the proxy onto these rails. The tier decision (apps door T2, Management door T3) and the
routing map live in the [identity-and-proxy](identity-and-proxy.md) spoke; the network layer is:

| Item | Value | Role |
|---|---|---|
| `HOST_PROXY_APPS` | `10.10.100.35` · VLAN 100 DMZ | the apps Caddy front door |
| `HOST_AUTHENTIK` | `10.10.80.37` · VLAN 80 Identity | forward-auth outpost target |
| Rule **200** | `NET_APP_CLIENTS` → `HOST_PROXY_APPS:PORT_WEB` | app clients reach *only* the proxy |
| Rule **240** | `HOST_PROXY_APPS` → `HOST_AUTHENTIK:PORT_AUTHENTIK` | proxy → Authentik (forward-auth) |
| Rule **250** | `HOST_PROXY_APPS` → `ROLE_APP_ORIGINS:PORT_APP_BACKENDS` | proxy → app origins (currently `:8080`) |
| Rule **830** | `Caddy → :53` (authoritative DNS) | **not widened for the apps proxy** — it validates ACME over the Cloudflare API on 443 (rule 810), not `:53` |

SKY-003 Phase 4 reconciles `ROLE_APP_ORIGINS` / `PORT_APP_BACKENDS` to the origins actually proxied
(karakeep-web listens on **3000**, not 8080 — a least-privilege fix), and audits SSH exposure of
`10.10.100.15:22`.

## Planned expansion

- **New VLAN / segment.** Admitted via new aliases + rules here, then DNS zones, then hosts — never
  by widening an existing role alias to mean two things.
- **Omada controller read reachability (SKY-018 P4).** The T1 network-gear collector needs to reach
  the Omada controller (`HOST_OMADA`, `10.10.50.25`, VLAN 50). Admitted by adding it to
  `ROLE_OPS_API_TARGETS` and its HTTPS management port to `PORT_OPS_API`, so existing rule 360 carries
  it — no new rule. Read-only reach; the credential and the T1/T3 split live in
  [access-and-trust](access-and-trust.md).
