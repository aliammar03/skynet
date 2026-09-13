---
summary: "Deploy or update a service through the Arcane GitOps loop: edit compose then PR then Arcane reconciles."
trigger: "Deploy or update a service"
tier: "T2 PR-gated"
executor: "scripts/gitops-deploy.sh, Arcane Git Sync, and skynet verify deployment"
rollback: "git revert"
---

# Runbook — deploy / update a service (Arcane GitOps, the skynet way)

**Tier:** T2 (PR-gated). **Executor:** `scripts/gitops-deploy.sh` + Arcane Git Sync +
`skynet verify deployment`. **Rollback:** `git revert`.

## Preconditions

- Identify the service, its persistent data, its intended ingress, and whether it needs encrypted configuration.

## Steps

### Apply the service standard

```
compose/<svc>/compose.yaml   # pinned image DIGESTS, env_file: .env, STRUCTURAL only
compose/<svc>/.env.git       # non-secret config, committed plaintext
compose/<svc>/.env.sops      # secrets only (sops+age); omit if the service has none
```

- **No inline `environment:` config** — put config in `.env.git`, not scattered in compose
  (structural keys like a computed `REDIS_URL` that interpolate a secret are the exception).
- **One role tag** via `x-arcane.tags` (`media`/`ai`/`books`/`bookmarks`/…, stable colour per
  role — see compose README). Arcane applies it on sync; `gitops-deploy.sh` reports/warns.
- **A healthcheck on every service** (image built-in or compose-declared) so Arcane reports
  `(healthy)` and dependents can use `condition: service_healthy`. Match the probe to the image's
  tools (curl/wget/node/bash-`/dev/tcp`) — see the compose README table. `gitops-deploy.sh` warns
  if any service lacks one.
- **No Docker file-secrets, no `*.txt` secrets.** One secret store: `.env.sops`.
- **Volumes:** simple file data → absolute `/opt/docker/appdata/<svc>/<role>` bind mounts
  (swept by `backup-restic.sh`). Database engines → **named** volumes, each labelled
  `skynet.service: <svc>` + `skynet.backup: protect|ephemeral` + `skynet.managed: gitops`
  (restic backs up the `protect` ones directly). Never relative in-project-dir data. Volume
  labels are immutable — to change them, recreate the volume (`down` → `docker volume rm` →
  redeploy). When switching a named volume to a bind mount, remove the orphan.

### Materialize the runtime environment

Arcane's **GitOps** sync copies `compose.yaml` (and the compose dir, incl. subdirs) from git and
owns the project lifecycle — but it does **NOT** merge `.env.git`/`project.env` into `.env`
(that layering is only for non-GitOps projects). `docker compose` just reads whatever `.env` is on
disk. So `scripts/gitops-deploy.sh` **materialises** the effective `.env` = `.env.git` +
`sops -d .env.sops`, written `0600` and owned by Arcane's project UID, decrypted on vm-skynet-ops
(the age key never leaves it).
Arcane leaves a populated `.env` untouched on re-sync, so the two coexist.

### Deploy or update an existing service

1. **Branch** `deploy/<svc>`; edit `compose/<svc>/*` per the standard. Validate:
   `cd compose/<svc> && printf '…dummy…' > .env && docker compose config -q && rm .env`.
2. **PR** with a teaching description (what it is, ports, front door, backup impact). **Ali merges.**
3. `scripts/gitops-deploy.sh <svc>` — the deployment procedure ensures the source sync,
   materialises `.env`, redeploys, and waits for the project. Its source selection, retry/wait,
   environment, and recovery behavior remain owned here; the verifier does not perform them.
4. Verify the exact merged deployment revision with the packaged, report-only observer:

   ```bash
   skynet verify deployment <svc> <full-revision>
   ```

   It checks the complete Arcane/Docker project at that revision, all container health, and every
   declared route. Routed checks use the Docker `dmz` network and verified TLS through
   `10.10.100.35`; HTTP 100–499, including 302/401, is acceptable. Unrouted services are reported
   as skipped. The route probe may create/remove an ephemeral container and cache its pinned image.
5. If verification fails, it reports the failed observation; it does not deploy, restart, or
   rollback. Prepare a reviewed inverse with `scripts/gitops-rollback.sh <svc> <full-revision> --prepare`,
   then human-review and merge the rollback PR before Arcane reconciles it.

## Verify

- `skynet verify deployment <svc> <full-revision>` succeeds. This requires exact revision identity,
  complete positive equal Arcane and Docker counts, every container running and healthy, and all
  declared routes reachable with valid TLS; a service with no declared route is explicitly skipped.

## Rollback

- Use the reviewed rollback PR prepared by `scripts/gitops-rollback.sh`; after its human merge, run
  `scripts/gitops-deploy.sh <svc>` to reconcile the reverted revision. The verifier never invokes
  rollback itself.

## Evidence

- Include the compose validation, deploy/health result, persistent-data impact, and any refreshed inventory in the PR or journal record.
