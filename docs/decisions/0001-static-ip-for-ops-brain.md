# ADR 0001 — Static IP for the ops brain (convention exception)

- **Status:** accepted
- **Date:** 2026-08-15
- **Context section of plan:** §1

## Context

The 4-digit VMID convention pairs with DHCP-assigned addressing for most guests. But
skynet-ops is the operations brain: the thing that must keep working when the network node
— and therefore OPNsense, and therefore DHCP — is the component that died.

## Decision

`vm-skynet-ops` gets **10.10.90.90 static**, configured via cloud-init (not DHCP). The
address is **reserved/excluded in OPNsense** so nothing collides. This is a deliberate,
documented exception to "addressing comes from DHCP."

## Consequences

- The ops brain is reachable during a DHCP outage — it can drive `DR-network-node.md`.
- `10.10.90.90` must be added to `ROLE_ADMIN_TARGETS` (covers workstation SSH + Management
  Caddy via existing rules 220/230) and recorded in IP Allocations.
- If OPNsense is rebuilt from `config.xml`, the reservation/exclusion is restored with it.
