---
summary: "Deploy or update a service: edit compose, PR with the dry-run effect, merge; skynet deploy applies, verifies, and rolls back by itself."
trigger: "Deploy or update a service"
tier: "T2 PR-gated"
executor: "skynet deploy (skynet-deploy timer: --pending --if-moved, every 30 s)"
rollback: "automatic to the last verified revision; git revert for a merged change"
---

# Runbook — deploy / update a service

**Tier:** T2 (PR-gated; merge is the approval). **Executor:** `skynet deploy`, run by the
`skynet-deploy` timer, which checks for a moved `main` every 30 seconds. **Rollback:** automatic return to the last
verified revision plus a revert PR; `git revert` for a merged change you want undone.
Design: [gitops-loop](../docs/design/gitops-loop.md).

## Preconditions

- Identify the service, its persistent data, its intended ingress, and whether it needs encrypted
  configuration.

## Steps

### Apply the service standard

```
compose/<svc>/compose.yaml   # pinned image DIGESTS, env_file: .env, STRUCTURAL only
compose/<svc>/.env.git       # non-secret config, committed plaintext
compose/<svc>/.env.sops      # secrets only (sops+age); omit if the service has none
```

- **No inline `environment:` config** — config lives in `.env.git` (a structural key that
  interpolates a secret, like a computed `REDIS_URL`, is the exception). A key in both `.env.git`
  and `.env.sops` is refused at deploy.
- **A healthcheck on every service** (image built-in or compose-declared); deployment verification
  fails without one. Match the probe to the image's tools — see the compose README table.
- **`name: <svc>`** if the compose sets a project name at all; it must match the directory.
- **No Docker file-secrets, no `*.txt` secrets.** One secret store: `.env.sops`.
- **Volumes:** simple file data → absolute `/opt/docker/appdata/<svc>/<role>` bind mounts. Database
  engines → **named** volumes labelled `skynet.service: <svc>` + `skynet.backup: protect|ephemeral`
  + `skynet.managed: gitops`. Repo-tracked config files → relative `./…:…:ro` mounts (they come
  from the revision's release directory). Never relative in-project data.

### Deploy or update

1. **Branch** `deploy/<svc>`; edit `compose/<svc>/*`; **commit** (the dry run reads git objects,
   not the working tree).
2. **Preview the effect** and paste it into the PR description:

   ```bash
   skynet deploy <svc> --dry-run HEAD
   ```

   It renders the service at your commit and at what runs now, and lists per container: image,
   ports, networks, volumes, labels, other settings, and the **names** of env keys added, removed,
   or changed (values are never shown).
3. **PR** with a teaching description (what it is, ports, front door, backup impact, the effect).
   **Ali merges** — that is the approval.
4. The timer deploys the merged revision within about a minute. To apply at once:
   `skynet deploy <svc>`. Every step lands in the operation record; read it with
   `skynet log --target svc/<svc>`.

### Remove a service

Delete `compose/<svc>/` in a PR (plus its Caddyfile/cloudflared routes, then `skynet withdraw`
for each removed vhost). After merge the timer retires the project: containers and networks come
down, its releases are removed, and its **named volumes are kept** — `skynet log --kind retire`
lists them for you to delete by hand once you are sure.

A new service deploys the same way; it has no rollback target until its first verified deploy,
so a failed first deploy stops (`no-rollback-target`) instead of guessing.

## Verify

- `skynet deploy` verifies by itself; re-check any time with `skynet verify deployment <svc>`:
  every container at the expected `skynet.revision`, running and healthy, no stray or missing
  container, and each declared route answering through the apps front door with valid TLS
  (HTTP 100–499). A service with no declared route reports routes `skipped`.

## Rollback

- **Automatic.** A failed deploy redeploys the host's `verified` revision, marks the failed one as
  held (the timer won't retry it), and opens `revert/<svc>-<rev>`. That PR merges itself when the
  [AGENTS.md §3](../AGENTS.md) gate holds; otherwise it waits for you. Merging it (or a fix)
  moves `main` and releases the hold.
- **By choice.** `git revert` the merged change in a PR; the timer deploys it.
- If the rollback itself fails (exit 4), a Pushover alert goes out; stop — that is a hard checkpoint. See
  [`diagnose/deploy-stuck.md`](diagnose/deploy-stuck.md).

## Evidence

- The PR's dry-run effect, the operation record line for the deploy, the verification output, and
  persistent-data impact.
