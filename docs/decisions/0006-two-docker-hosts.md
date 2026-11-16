---
status: accepted
date: 2026-10-21
decision-makers: Ali
---

# Two Docker hosts: docker-dmz for apps, docker-admin for the rest

## Context and Problem Statement

Apps reachable from the internet shouldn't share a host with the admin door, the logins and the
monitoring, and the monitoring has to survive losing a node.

## Decision Outcome

Chosen option: **docker-dmz** (the apps, on the core node, VLAN 100) and **docker-admin** (the
admin door, admin Authelia, Gatus and the observability stacks, on the network node, VLANs 50 and
60), because that segments them, and monitoring survives losing the core node.

### Consequences

- Good, because the DMZ reaches the management VLAN only through one write-only port, vlagent's
  (`docs/lab.md` → OPNsense).
- Bad, because each host has its own door, Authelia, backup stack and heartbeat.

## More Information

Ali, 2026-10-21, at the start.
