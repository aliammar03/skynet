# Runbook — deploy / update a service (Arcane GitOps, the skynet way)

**Tier:** T2 (PR-gated). **Executor:** `scripts/gitops-deploy.sh` + Arcane Git Sync. **Rollback:** `git revert`.

## The standard (every service looks the same)

```
compose/<svc>/compose.yaml   # pinned image DIGESTS, env_file: .env, STRUCTURAL only
compose/<svc>/.env.git       # non-secret config, committed plaintext
compose/<svc>/.env.sops      # secrets only (sops+age); omit if the service has none
```

- **No inline `environment:` config** — put config in `.env.git`, not scattered in compose
  (structural keys like a computed `REDIS_URL` that interpolate a secret are the exception).
- **No Docker file-secrets, no `*.txt` secrets.** One secret store: `.env.sops`.
- **Volumes:** simple file data → absolute `/opt/docker/appdata/<svc>/<role>` bind mounts
  (swept by `backup-restic.sh`). Database engines → **named** volumes, each labelled
  `skynet.service: <svc>` + `skynet.backup: protect|ephemeral` + `skynet.managed: gitops`
  (restic backs up the `protect` ones directly). Never relative in-project-dir data. Volume
  labels are immutable — to change them, recreate the volume (`down` → `docker volume rm` →
  redeploy). When switching a named volume to a bind mount, remove the orphan.

## How env actually reaches the container (important)

Arcane's **GitOps** sync copies `compose.yaml` (and the compose dir, incl. subdirs) from git and
owns the project lifecycle — but it does **NOT** merge `.env.git`/`project.env` into `.env`
(that layering is only for non-GitOps projects). `docker compose` just reads whatever `.env` is on
disk. So `scripts/gitops-deploy.sh` **materialises** the effective `.env` = `.env.git` +
`sops -d .env.sops`, written `0600 root`, decrypted off-host (age key never leaves vm-skynet-ops).
Arcane leaves a populated `.env` untouched on re-sync, so the two coexist.

## Deploy / update an existing service

1. **Branch** `deploy/<svc>`; edit `compose/<svc>/*` per the standard. Validate:
   `cd compose/<svc> && printf '…dummy…' > .env && docker compose config -q && rm .env`.
2. **PR** with a teaching description (what it is, ports, front door, backup impact). **Ali merges.**
3. `scripts/gitops-deploy.sh <svc>` — ensures the sync, materialises `.env`, redeploys, health-checks.
   (During a migration you may verify off a branch first: `GITOPS_BRANCH=<branch> scripts/gitops-deploy.sh <svc>`.)
4. If red → `git revert`, re-run `gitops-deploy.sh <svc>`.

## One-time cutover of a legacy (non-GitOps / filesystem) project

Only needed the first time a hand-managed project moves to GitOps. **Destructive.**

1. Confirm data is on absolute appdata or named volumes (destroy won't touch appdata; a new compose
   project **name** gives fresh named volumes — fine only when data is disposable/rebuildable).
2. `POST projects/{id}/down` then `DELETE projects/{id}/destroy` (removes containers + old project dir).
3. `scripts/gitops-deploy.sh <svc>` creates the GitOps project fresh and deploys.
