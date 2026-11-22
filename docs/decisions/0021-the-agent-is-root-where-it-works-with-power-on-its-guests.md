---
status: accepted
date: 2026-11-22
decision-makers: Ali
---

# The agent is root on the hosts it works on, with power over their guests, and never merges

Supersedes ADR-0011, adding the Proxmox token for power.

## Context and Problem Statement

ADR-0011 made the agent root on the hosts it works on, so a fix needs no step from Ali. The merge
window (`docs/plans/autonomy.md`, step 5) also reboots a host whose kernel changed, one a night.
On a host where it is root, `sudo reboot` does that. But it can't start a guest that doesn't come
back, and it can't reboot ops, where the agent is a plain user. Proxmox can, through a token,
and a token's reach is set in Proxmox, which is Ali's.

## Considered Options

- **`sudo reboot` on each host, and Ali's console for one that hangs:** no new credential, but
  ops can't be rebooted at all, and a hung guest waits for Ali.
- **A Proxmox token for power only, on a pool of the agent's guests:** VM.PowerMgmt and VM.Audit,
  nothing else, on the guests git describes.
- **A token with more** (snapshots, config): the first is the plan's Open item, a snapshot before a
  reboot; config is Provisioning's, with its own token (step 8).

## Decision Outcome

Chosen option: everything ADR-0011 grants, unchanged, plus **`skynet@pve!operate` on each node**
(they aren't clustered). It has role `SkynetPower` (VM.PowerMgmt and VM.Audit) on pool `skynet`:
ops, docker-dmz, technitium-core and PBS on core; docker-admin and technitium-network on network.
Ops holds it (`hosts/ops/secret.sops.yaml`, as a header file curl reads), and Ali mints it. It
reboots a guest whose kernel changed, in the window, and starts or resets one that doesn't come
back. It can't change a guest, its disks, storage, users or tokens, and it can't touch a guest
outside the pool (Unraid, OPNsense, HAOS, Omada, athena). Because power over the agent's own
guests is what a reboot needs, and a pool keeps it off everything else.

The rest stands as ADR-0011 has it:
- root on docker-admin, docker-dmz, PBS (VM 2040), technitium-network and technitium-core:
  passwordless sudo on the NixOS hosts (`agentRoot`, `modules/base.nix`), root over SSH from ops on
  PBS;
- both doco-cd MCP servers' restart, job and compaction tools, with destroying a project or
  removing a stack asking Ali each time;
- an Alertmanager silence for its own planned work, ending within 4 hours, its comment naming the
  work;
- never printing a secret value or decrypting one on purpose, no sudo, Docker socket or private age
  key elsewhere, a plain user on ops, and no merge.

### Consequences

- Good, because a kernel update finishes without Ali, ops's included, and a guest that hangs on
  its reboot is started again.
- Bad, because a token that can power guests off could stop the lab's services. Its use is the
  window's, one guest a night, each back and verified before the next.
- Bad, as before: root on those hosts reads every secret on them, and "never merge" is a soft wall
  outside the code owners' files (ADR-0013).

## More Information

The history of the lanes is in ADR-0011. The autonomy plan, which Ali merged on 2026-11-15 (#185),
proposed the token for power, scoped to a pool. Its PR is step 5's third (2026-11-22), and Ali's
merge accepts this record. Until step 6 the window only logs its reboots.
