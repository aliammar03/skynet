---
status: accepted
date: 2026-10-31
decision-makers: Ali
---

# Remote access is Tailscale, with OPNsense as the subnet router

## Context and Problem Statement

Ali needs the lab from outside the house: the admin names, the apps, and the management network
for break-glass. Nothing inbound should open.

## Considered Options

- WireGuard on OPNsense (the earlier plan);
- Tailscale, with `os-tailscale` on OPNsense.

## Decision Outcome

Chosen option: **Tailscale**, with `os-tailscale` on OPNsense as the subnet router and split DNS
for `aliammar.net` (Technitium's two servers), because nothing inbound opens, and it keeps working
when docker-admin or a node is down, so it reaches what needs fixing. ops is a node too, `tag:ops`,
in userspace.

### Consequences

- Good, because a phone on mobile data opens the admin and app names and the management network.
- Bad, because the tailnet's policy, its routes' approval and the node keys live in Ali's Tailscale
  account, outside git (`docs/lab.md` → Tailscale).

## More Information

Ali, 2026-10-23, with the DNS and remote-access plan (#36); ops on the tailnet 2026-10-31 (#139).
