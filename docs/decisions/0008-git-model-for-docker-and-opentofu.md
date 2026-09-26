# ADR 0008 — One git model for Docker services and OpenTofu

- **Status:** proposed — Docker half implemented by SKY-025 Phase 13 (`skynet deploy`); becomes
  accepted when Phase 15 lands the OpenTofu half
- **Date:** 2026-09-23

## Context

Docker services and OpenTofu resources use two different paths from git to running state, and each
has a gap:

- **Docker.** Arcane Git Sync polls `main` and redeploys `compose.yaml`; separately,
  `gitops-deploy.sh` decrypts `.env.sops`, writes `.env` into Arcane's project directory through a
  throwaway container, and restarts. Two actors deploy one service with no shared revision, so env
  and compose can go live out of order, and the env write depends on Arcane leaving that file alone.
  A failed deploy stays broken until a revert PR is human-merged.
- **OpenTofu.** One root holds four actuators (`proxmox-core`, `proxmox-network`, `technitium-dns`,
  `cloudflare-dns`), so `tofu-apply.sh` must reject mixed-scope plans at runtime. The reviewer of the
  source PR sees code, not the plan; the exact plan is shown for a second approval after merge.
  Encrypted state lives only on the ops VM (`runbooks/dr/DR-core-node.md`: if lost, re-import every
  guest) — a system-class thing not recoverable from git, which AGENTS.md §6 calls a bug.

## Decision

One model for both, in five parts:

```text
PR      the change + its predicted effect + bin/check          (what will happen)
merge   Ali approves that effect                              (the only approval)
execute one executor applies the exact merged revision,       (skynet deploy / skynet tofu apply)
        and refuses if the effect differs from the PR's
record  the running revision is written where git can see it  (labels, state branch, inventory)
recover automatic return to the last verified state, then a revert PR makes main match
```

### Docker services

1. **Layout unchanged:** `compose/<svc>/{compose.yaml,.env.git,.env.sops}`.
2. **Effect in the PR.** `skynet deploy <svc> --dry-run` renders the resolved compose diff: images,
   ports, volumes, and the *names* of changed env keys, never values. The PR description carries it.
3. **One executor.** After merge, `skynet deploy <svc>` on the ops VM fetches the exact merged
   revision, decrypts env in memory, and runs `docker compose up` over the Docker context with env and
   compose together. Arcane stays as a read-only dashboard; its Git Sync is turned off.
4. **Record.** Every container gets a `skynet.revision=<sha>` label, so the running revision is
   observable on the host itself; the nightly lifts it into `inventory/`.
5. **Recover.** If verification fails, the executor redeploys the last verified revision for that
   service (a state Ali already approved) and opens the revert PR. Returning to an approved, verified
   revision is not new authority — this is the basis for deploys reaching A4.

### OpenTofu

1. **One stack per actuator:** `tofu/proxmox-core/`, `tofu/proxmox-network/`,
   `tofu/technitium-dns/`, `tofu/cloudflare-dns/`, each with its own state and lock. Scope becomes a
   directory, so a mixed plan cannot exist; the runtime scope check goes away.
2. **Plan in the PR.** The author runs `skynet tofu plan <stack>` (T2 read credentials) and puts the
   human-readable plan plus a hash of its normalized resource changes in the PR description.
3. **Merge is the approval.** After merge, `skynet tofu apply <stack>` plans from the merged revision,
   requires the same normalized-change hash as the PR, and applies that saved plan. A different hash
   (drift, or a later change) stops with the new plan for a fresh PR. Delete/replace is still refused,
   protected guests are still refused, and snapshots/rollback for existing guests are unchanged.
4. **State in git.** Each stack's state, already encrypted by OpenTofu with the sops-held passphrase,
   is committed by the executor to a dedicated `tofu-state` branch after every apply. `main` stays
   code-only; the system rebuilds from `main` + `tofu-state`. Applies are serialized by a local lock.
5. **Drift.** The nightly runs a read-only plan per stack and reports any non-empty plan.

## Consequences

- One human approval per change, made while looking at the actual effect.
- Deploys get automatic rollback; outages from a bad deploy last minutes, not until Ali is online.
- Losing the ops VM no longer loses Tofu state.
- Arcane Git Sync and `gitops-deploy.sh` retire; the state split is a one-time `tofu state mv`
  migration per resource, done as a supervised saved-plan step.
- Needs human-merged changes to AGENTS.md §4 and `docs/system-design.md` (approval moves into the PR;
  deploy rollback is automatic). Those land with the phases, not with this ADR.
- Rejected: committing state to `main` (churns every PR and races reviews); a remote state service
  (a new system to run and back up); keeping Arcane Git Sync alongside the executor (two actors).
