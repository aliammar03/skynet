---
status: accepted
date: 2026-10-26
decision-makers: Ali
---

# Hosts are NixOS, kept current by comin

## Context and Problem Statement

A host has to rebuild from git alone, and nothing outside the lab may push into it. Something on
each host has to apply what `main` says.

## Decision Outcome

Chosen option: one NixOS flake for every host the lab runs, each host kept current by **comin**,
which pulls `main` every 60 s and switches to it, because a host then rebuilds from git and needs
no central push credential.

### Consequences

- Good, because a rebuilt host is its config in git plus its app data (`runbooks/restore.md`).
- Good, because a failed build keeps the running generation, and comin posts the failure to
  `#alerts`.
- Bad, because a broken comin can't deploy its own revert. comin is pinned to a commit
  (`flake.nix`) until a host change proves itself under a timed rollback before it merges
  (`docs/plans/autonomy.md`).
- Neutral, because the machines that aren't NixOS (PBS, the Proxmox nodes, Unraid) are described
  in git by the files and scripts applied to them (`hosts/README.md`).

## More Information

Ali, 2026-10-21. comin's testing branches are off since 2026-10-26 (#86): otherwise comin deploys
any `testing-<host>` branch on top of `main` as root, with no PR or merge, and the bot can push
branches. Only `main` reaches a host (`modules/base.nix`).
