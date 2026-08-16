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
| OS | Ubuntu 24.04 LTS, cloud image + cloud-init |
| Resources | 4 vCPU · 6 GB RAM · 60 GB disk |
| Base tools | `git curl jq tmux qemu-guest-agent unattended-upgrades age sops restic rclone`, Docker, Node 22 |

**Why the static IP** (ADR [0001](../decisions/0001-static-ip-for-ops-brain.md)): the ops brain
must keep its address when DHCP — i.e. OPNsense — is the very thing that died. It is
reserved/excluded in OPNsense so nothing collides, and it lives in `ROLE_ADMIN_TARGETS`. This is
the one exception to "addressing comes from DHCP," and it exists so Skynet can drive
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

## The blast-radius boundary, at the network layer

`ROLE_OPS_SSH_TARGETS` is the SSH half of the write blast radius (the pool set is the Proxmox
half — see [access-and-trust](access-and-trust.md)). A host is reachable for operate/grant work
**only** once it's in this alias. Adding a host here is part of the "new managed host" extension
point in the constitution.

## Planned expansion

- **Reverse proxy / ingress.** A Skynet-managed edge for internal services would add a rule set
  (and likely a `PORT_OPS_PROXY` alias) and a tier decision — today the Management Caddy is T3.
  This is the seed of a future `identity-and-proxy` spoke; when it lands, the proxy's targets and
  ports are defined here (or split out) rather than bolted onto the operate rules.
- **New VLAN / segment.** Admitted via new aliases + rules here, then DNS zones, then hosts — never
  by widening an existing role alias to mean two things.
