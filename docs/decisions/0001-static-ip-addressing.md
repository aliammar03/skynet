# ADR 0001 — Static IP addressing for Skynet guests

- **Status:** accepted
- **Date:** 2026-08-15 (revised 2026-08-17 — see *History*)
- **Context section of plan:** §1

## Context

Skynet's fleet is small and long-lived. Guests need addresses that are predictable (so a machine
can validate `VMID = VLAN + last octet`), that don't silently change, and — for the ops brain
specifically — that survive the loss of DHCP itself. DHCP-assigned addressing gives none of the
first two and actively breaks the third: skynet-ops (10.10.90.90) is the operations brain, the
thing that must keep working when the network node — and therefore OPNsense, and therefore DHCP —
is the component that died.

## Decision

**Static addressing is the standard for every Skynet guest.** Each guest gets a static IP via
cloud-init (not DHCP), with the last octet matching the 4-digit VMID convention
(`VMID = VLAN + last octet`). Addresses are **reserved/excluded in OPNsense** so nothing collides.
**DHCP is the exception**, used only where a guest genuinely doesn't warrant a reservation.

`vm-skynet-ops` gets **10.10.90.90 static** like every other guest — it is special only in that
its reservation is load-bearing for disaster recovery, not in *being* static.

## Consequences

- Addresses are predictable and machine-checkable; no guest silently moves.
- The ops brain is reachable during a DHCP outage — it can drive `runbooks/dr/DR-network-node.md`.
- `10.10.90.90` is in `ROLE_ADMIN_TARGETS` (covers workstation SSH + Management Caddy via existing
  rules 220/230) and recorded in IP Allocations.
- If OPNsense is rebuilt from `config.xml`, the reservations/exclusions are restored with it.
- New guests are provisioned with a static IP as the default (see `runbooks/provision-vm.md`).

## History

- **2026-08-15** — originally accepted narrowly, as *"static IP for the ops brain, a documented
  exception to DHCP-by-default."*
- **2026-08-17** — reversed the default: static addressing is now the standard for all guests,
  DHCP the exception. The ops brain's static IP is no longer framed as special. Corrected in place
  (this ADR records the current convention; the git history holds the prior wording).
