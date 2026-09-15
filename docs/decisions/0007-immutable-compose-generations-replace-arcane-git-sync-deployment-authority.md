# ADR 0007 — immutable Compose generations replace Arcane Git Sync deployment authority

- **Status:** accepted
- **Date:** 2026-09-15

## Context

P11's old Git Sync design could expose source before the selected effective environment and Arcane's
manual sync lacked an operation identity or in-flight lease for bounded write reconciliation.
Deployment correctness requires one coherent source/environment snapshot and a recoverable account of
what Docker is actually running. The existing T2 path already reaches the Docker host through
`svc-ops`, with Docker Compose and a persistent protected home.

## Decision

Skynet prepares the complete Compose runtime subtree and layered environment from one exact full Git
revision as an immutable protected remote generation. It activates directly through Docker Compose
under a per-service host `flock`, observes Docker generation metadata independently, verifies complete
health and declared DMZ routes, and promotes the generation to stable only after that verification.
It retains previous stable state and provides explicit, human-controlled generation rollback without
changing authored Git. Arcane may observe and help a human in emergencies but is not a deployment
source or activation authority. Enabled Arcane auto-sync prevents direct activation.

## Consequences

Deployment state is a small filesystem tree on the persistent Docker host rather than an Arcane sync
record. Failed candidates may be active while the old stable generation remains the rollback candidate.
Interrupted application requires lock and Docker reconciliation; same-generation convergence is allowed
once safe, while a different generation is refused over ambiguity. Runtime rollback can intentionally
diverge from reviewed authored Git until a normal correction PR lands. P11 is supervised T2 and has no
automatic rollback; an A4 promotion would need a separate dumb, failure-tested rollback executor.

<!-- ADRs are amended IN PLACE, never superseded (docs/conventions/docs.md). When this decision
     changes, edit THIS file to state what's true now and add a dated line under History. -->
