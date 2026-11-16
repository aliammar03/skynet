---
status: accepted
date: 2026-10-23
decision-makers: Ali
---

# No OpenTofu: VMs come from `proxmox.sh`

## Context and Problem Statement

Our VMs have to be created and changed somehow. Guests change rarely.

## Decision Outcome

Chosen option: no OpenTofu. Each VM comes from its versioned `hosts/<h>/proxmox.sh`, the exact
`qm create`, which Ali runs on the node: re-runnable documentation, not automation. Internal DNS
records live in `dns/aliammar.net.zone`. The Cloudflare wildcard CNAME is set once by hand.
Because guests change rarely, and nothing in the lab then holds a credential that creates VMs.

### Consequences

- Good, because nothing in the lab can create, change or destroy a VM.
- Bad, because each VM's spec is a script Ali runs by hand, and nothing notices when PVE drifts
  from it.

## More Information

Ali, 2026-10-21; the internal records in `dns/` from the DNS plan (2026-10-23, #36). A plan to
create and change our VMs with OpenTofu, under a token scoped to pool `skynet`, is in
`docs/plans/autonomy.md` → Provisioning. Until it merges, this record stands.
