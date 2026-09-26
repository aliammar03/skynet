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
   → `skynet verify deployment <svc> <full-revision>` observes revision, project/container health,
     and declared ingress routes (report-only)
   → agent commits refreshed inventory
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

Deployment orchestration and recovery remain separate from verification. `gitops-deploy.sh` owns
source selection, sync polling/retry, environment materialization, and redeploy/restart. With
`--gate`, it resolves the exact 40-hex head of local `refs/heads/$GITOPS_BRANCH` (default `main`)
for the selected sync and passes that revision to the packaged verifier through
`scripts/deploy-gate.sh`. The verifier call accepts only the service and expected revision;
recovery uses a separate `<deploy-commit>` identity, and `gitops-rollback.sh` prepares an explicitly
reviewed inverse after an operator chooses to recover.

Service recovery follows [`restore-service.md`](../../runbooks/restore-service.md); its restore
revision includes the matching `.env.git` and `.env.sops` files. See [backup strategy](../backup-strategy.md).

## Image pinning & updates

Every `compose.yaml` pins an **exact version tag**. **Renovate** (Mend's free GitHub App, private
repos, first-class docker-compose manager) watches the repo and opens one PR per bump with release
notes embedded. Arcane's auto-update stays off for git-synced projects.

Review updates through their Renovate PRs, then deploy through [`deploy-service.md`](../../runbooks/deploy-service.md).
If deployment verification reports an unhealthy result, prepare a reviewed inverse with
[`gitops-rollback.sh`](../../scripts/gitops-rollback.sh), human-merge its PR, and let Arcane
converge to that revision; the verifier never invokes rollback.

## Live facts (census 2026-09-26, SKY-025 P12)

What the Phase 13 deploy executor replaces. Re-check before relying on it.

- **Arcane:** `http://10.10.100.15:3552`, environment `0`, one registered repo `Skynet`
  (`https://github.com/aliammar03/skynet.git`, http auth). Ten Git Syncs, one per `compose/<svc>/`
  except `arcane-manager` (run by hand at `/opt/docker/arcane-manager`, with `docker.sock` and
  `/opt/docker/arcane-projects` bind-mounted). Each sync: branch `main`, `compose/<svc>/compose.yaml`,
  `syncDirectory: true`, interval 180 s, `autoSync: true` except **librespeed (off)**.
- **Revision source:** the sync's `lastSyncCommit`: the newest commit on `main` that touched a synced
  file. The project reports the same field.
- **Project dirs:** `/opt/docker/arcane-projects/<svc>`, owned `1000:1000`, mode `0700` (parent `0755`).
  svc-ops cannot traverse them; reads and writes go through the docker group.
- **Materialized env:** `<project dir>/.env`, owner `1000:1000`. Six are `0600`; **aiostreams, calibre,
  karakeep, marinara are `0644`**, so only their `0700` parent contains them.
- **Mounts:** payload under `/opt/docker/appdata/<svc>/…` binds, plus named volumes
  (`aiometadata_{redis,jikan_redis,jikan_mongo,jikan_typesense}_data`, `karakeep_meili_data`,
  `obsidian-livesync_data`). Config files are bind-mounted from the project dir: cloudflared
  `config.yml`, caddy-apps `Caddyfile`, obsidian-livesync `local.ini`, aiometadata `jikan/*`.
  cloudflared also mounts `appdata/cloudflared/creds/credentials.json`.
- **Out-of-band deploy:** `librespeed` runs from
  `/home/svc-ops/.local/state/skynet-deploy/librespeed/generations/<f8072b3…>` (state files `active`,
  `stable-state.json`, `operations/`), activated by the unmerged `phase/sky-025-p11-deploy` prototype.
  It is not reconstructable from `main`. Phase 13 adopts or retires it.
- No container carries a `skynet.revision` label yet.
