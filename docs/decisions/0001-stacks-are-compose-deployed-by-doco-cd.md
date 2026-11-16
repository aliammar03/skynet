---
status: accepted
date: 2026-10-21
decision-makers: Ali
---

# Stacks are Docker Compose, deployed by doco-cd

## Context and Problem Statement

The apps run in containers. Something on each Docker host has to apply what `main` says, decrypt
the stacks' secrets there, and put back what drifts, with nothing inbound and no deploy credential
outside the lab.

## Decision Outcome

Chosen option: Docker Compose stacks, one folder each under `stacks/<target>/`, deployed by
**doco-cd** on each Docker host, because it is the simplest mature GitOps tool that keeps Compose:
it polls `main`, decrypts sops files with the host's key, discovers stacks by folder and
reconciles them. Renovate already understands Compose.

### Consequences

- Good, because a stack is one folder: adding or removing the folder adds or removes the stack
  (`stacks/README.md`).
- Good, because Renovate bumps the pinned images where they are.
- Bad, because doco-cd redeploys a whole stack when one of its containers dies, so a flaky
  container gets a stack of its own (`stacks/admin/exporters`, `stacks/admin/omada-exporter`).
- Bad, because doco-cd writes decrypted secrets into the stack's folder, so no container mounts
  the folder whole.

## More Information

Ali, 2026-10-21, at the start. doco-cd's settings are `.doco-cd.<target>.yml` and
`modules/docker-host.nix`.
