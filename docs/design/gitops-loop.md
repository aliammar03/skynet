---
summary: "How a service change becomes a running container via Arcane, with git-revert rollback and image pinning + Renovate."
---

# Spoke · The GitOps loop

> How a change to a service becomes a running container, and how versions stay pinned and current.
> Governed by [`../system-design.md`](../system-design.md). Compose rules: [conventions](../conventions.md).

## The truth model

Two private GitHub repos:

- **`skynet`** — operational truth: `AGENTS.md`, `.sops.yaml`, `docs/`, `inventory/` (auto-generated
  JSON, never hand-edited), `compose/<svc>/`, `scripts/`, `runbooks/`, `bin/ops`.
- **`skynet-opnsense`** — automatic pushes from the OPNsense **os-git-backup** plugin: every
  firewall change auto-commits `config.xml`. Complete firewall/DHCP/alias truth with zero standing
  management-plane access — and, critically for DR, **the router config survives the router**.

## The loop

```
edit compose/<svc>/ → branch → PR → Ali merges
   → Arcane Git Sync polls, pulls, reconciles (project read-only in the UI)
   → agent verifies health via Arcane API / docker context, commits refreshed inventory
```

- **One Arcane Git Sync per project dir**, auto-sync on; Arcane's own auto-update polling **off**
  for git-synced projects (one reconciler, one truth).
- **Rollback = `git revert`.** A failed health gate does not mutate its checkout. The explicit,
  review-branch rollback executor is [`gitops-rollback.sh`](../../scripts/gitops-rollback.sh);
  its decision and limits are in [actuators](actuators.md). SSH + `docker context` is break-glass
  access when Arcane is unavailable.
- **Env materialization** belongs to `gitops-deploy.sh`: committed `.env.git` + decrypted
  `.env.sops` → effective `0600` `.env`. Arcane GitOps does not merge `project.env`; every service
  consumes the wrapper-built file through `env_file: .env`.
- Auto-sync **only redeploys projects already running** — a stopped project updates on its next
  manual start (matters during maintenance windows).

Service recovery follows [`restore-service.md`](../../runbooks/restore-service.md); its restore
revision includes the matching `.env.git` and `.env.sops` files. See [backup strategy](../backup-strategy.md).

## Image pinning & updates

Every `compose.yaml` pins an **exact version tag**. **Renovate** (Mend's free GitHub App, private
repos, first-class docker-compose manager) watches the repo and opens one PR per bump with release
notes embedded. Arcane's auto-update stays off for git-synced projects.

Review updates through their Renovate PRs, then deploy through [`deploy-service.md`](../../runbooks/deploy-service.md).
An unhealthy deployment is reverted in git and Arcane converges to that revision.
