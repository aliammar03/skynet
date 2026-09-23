---
id: SKY-027
title: "One deployment model: NixOS Docker host with compose2nix, deploy-rs and sops-nix"
status: draft
horizon: long
created: 2026-09-23
updated: 2026-09-23
phases: 4
current_phase: 0
tier_touched: [T1, T2, T2+]
related:
  - docs/system-design.md
  - docs/decisions/0008-git-model-for-docker-and-opentofu.md
  - docs/design/gitops-loop.md
  - flake.nix
  - compose/
  - tofu/vm-docker-dmz.tf
---

# SKY-027 · One deployment model: NixOS Docker host with compose2nix, deploy-rs and sops-nix

> Deploy Docker services the same way NixOS hosts already deploy — one mechanism, one secrets path,
> automatic rollback built in — and retire Arcane.

**Start only after SKY-025 is archived.** SKY-025 Phase 13 delivers `skynet deploy` (ADR 0008),
which fixes the two-actor problem on today's Docker host. This directive is the larger step after it.

## 1. Problem / motivation

Skynet runs two deployment models:

| | NixOS hosts (ops VM, AdGuard CT) | Docker services (`vm-docker-dmz`, ~11 projects) |
|---|---|---|
| Mechanism | deploy-rs from the flake | Arcane Git Sync today; `skynet deploy` after SKY-025 |
| Secrets | sops-nix, rendered on the host | `.env.sops` decrypted on the ops VM, pushed over SSH |
| Rollback | deploy-rs `magicRollback`/`autoRollback`, automatic | executor redeploys last verified revision |
| Host OS | declared in git | Ubuntu VM, configured by hand plus Tofu envelope |

Two models means two sets of mechanics to learn, test, and recover. The Docker host is also the one
workload VM whose OS is not rebuildable from git.

## 2. Brainstorm — options considered

- **Option A — keep Ubuntu + `skynet deploy` (ADR 0008).** Smallest change; already planned. Leaves
  the host OS outside git and keeps a second secrets path.
- **Option B — NixOS host, compose2nix.** `compose.yaml` stays the source (Renovate keeps working);
  compose2nix generates NixOS modules that run each project as systemd-managed containers.
  deploy-rs deploys, sops-nix renders env, rollback is deploy-rs's. Arcane retires.
- **Option C — NixOS host, native `virtualisation.oci-containers`.** Cleanest Nix, but abandons
  compose files, so Renovate's compose manager and the house compose conventions go away.
- **Option D — Kubernetes (k3s) + Flux.** Real GitOps with health-based rollback, far more machinery
  than an 11-service lab needs.
- **Decision (proposed):** **B**, if Phase 1's spike shows compose2nix handles every current project
  (healthchecks, named volumes, labels, networks, the Caddy front door) without hand-editing output.

## 3. The plan

- **Scope:** the DMZ Docker host and its compose projects. Non-goals: new services, Kubernetes, the
  Management Caddy (T3).
- **Hosts & tiers touched:** `vm-docker-dmz` (10015, ops-managed pool, T2); a rebuild needs a T2+
  grant. The constitution PR records that Docker services deploy through deploy-rs.
- **Rollback posture:** keep the Ubuntu VM stopped, not destroyed, until the NixOS host has run a
  full week; restic payload backups restore onto either.
- **Grants / human actions:** one T2+ grant on the new host per migration phase; Ali approves the
  cutover window.

### Phase 1 — spike   `[ ]` not started   · review: Light
Run compose2nix over every `compose/<svc>/` in a throwaway NixOS VM from `lxc-base`/a VM template.
Exit evidence: every project starts healthy from generated modules; a list of any output that needs
hand edits (zero is the bar for choosing B).

### Phase 2 — host + one service   `[ ]` not started   · review: Full
Declare `hosts/vm-docker-nix` in the flake with sops-nix and deploy-rs; migrate one low-risk service
(`librespeed`) with its payload. Exit evidence: deploy-rs deploy, forced bad deploy rolls back
automatically, payload restore verified.

### Phase 3 — migrate the rest   `[ ]` not started   · review: Full
Move the remaining projects in batches, Caddy front door last. Exit evidence: every route verified from
the DMZ vantage; `skynet verify` green for all services.

### Phase 4 — retire   `[ ]` not started   · review: Full
Retire Arcane and the Ubuntu VM (a ⚠ hard checkpoint: destroy is Ali's action), delete the Docker
branch of `skynet deploy`, update the constitution and gitops-loop spoke. Exit evidence: one
deployment model in docs and code.

## 4. Status
Current: idea, not started. Next: promote after SKY-025 is archived.

## 5. Prompts
Execute / review: [`planning/prompts/`](../prompts/README.md) with this directive's path.

## 6. Status log
- 2026-09-23 — created (draft) from the deployment-model review on PR #260.
