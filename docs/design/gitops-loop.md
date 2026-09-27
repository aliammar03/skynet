---
summary: "How a merged compose change becomes running containers through skynet deploy: one revision, env and compose together, automatic return to the last verified revision."
---

# Spoke · The GitOps loop

> How a change to a service becomes a running container, how a bad one is undone, and how versions
> stay pinned and current. Governed by [`../system-design.md`](../system-design.md) and
> [ADR 0008](../decisions/0008-git-model-for-docker-and-opentofu.md). Compose rules:
> [conventions](../conventions.md).

## The truth model

Two private GitHub repos:

- **`skynet`** — operational truth: `AGENTS.md`, `.sops.yaml`, `docs/`, `inventory/` (generated,
  never hand-edited), `compose/<svc>/`, `runbooks/`, the `skynet` engine.
- **`skynet-opnsense`** — automatic pushes from the OPNsense **os-git-backup** plugin: every
  firewall change auto-commits `config.xml`, so the router config survives the router.

## The loop

```
PR      compose/<svc>/ change + `skynet deploy <svc> --dry-run` effect + bin/check
merge   Ali — the only approval
apply   skynet-deploy timer (every 30 s): `skynet deploy --pending --if-moved`
verify  every container at the revision, running, healthy; declared routes answer
recover automatic redeploy of the last verified revision, then a revert PR that merges itself
        when the AGENTS.md §3 gate holds
watch   `skynet watch` every 5 min; an outage reaches Ali's phone (observability spoke)
```

A service's **revision** is the newest commit on `origin/main` that touched `compose/<svc>/`.
`--pending` deploys each service whose revision differs from the one running, skipping projects
marked `x-skynet: {deploy: manual}` (the Arcane controller itself).

**The trigger.** Every 30 s the timer asks `git ls-remote origin refs/heads/main`. The full pass
runs when `main` moved since the last pass, or the last clean pass is 15 min old. A pass with an
`unavailable` result retries with backoff (1, 2, 4, … min, capped at 15), so a lasting outage
doesn't run a full pass every tick (`state/main-seen.json`). There is no webhook: nothing
internet-facing reaches the ops VM.

**Retirement.** A project on the Docker host that carries `skynet.service` but has no
`compose/<svc>/compose.yaml` on `main` is retired by the same pass, on the write-path shape:
`docker compose -p <svc> down --remove-orphans` (never `-v`), verified by no container left, then
its releases and host facts under `/opt/docker/services/<svc>/` are removed. **Named volumes are
kept** — deleting payload stays a human act; the operation record lists them (`volumes-kept`). A
project with a writable bind mount into its release directory is refused (retire it by hand). If
`main` lists no services at all, nothing is retired. A failed retirement redeploys the verified
revision.

**The revert auto-merge.** After each pass, open `revert/<svc>-<12hex>` PRs go through the
[AGENTS.md §3](../../AGENTS.md) gate (`src/skynet/automerge.py`): opened by the executor, only
`compose/<svc>/` changed, its tree identical to the host's `verified` revision, `main` still at the
failed revision, `bin/check` green on the head. The merge pins that head
(`--match-head-commit`); because that doesn't pin `main`, the squash commit's `compose/<svc>/` is
then required to be exactly the verified tree, and anything else is `rollback-failed` (alerts). Any failed check is recorded once per head and leaves the PR for Ali.

## One deploy

`skynet deploy <svc>` runs the [write-path shape](actuators.md):

1. **Preflight.** The revision must be merged to `origin/main`. The service is rendered on the ops
   VM from git objects (never the working tree): `.env.git` + the decrypted `.env.sops` become a
   `0600` `.env` in a tmpfs directory, and Compose resolves the project to JSON
   (`config --no-path-resolution`: env inlined, relative paths kept, `$` escaped). Every service
   gets the labels `skynet.revision=<rev>` and `skynet.service=<svc>`. Images are pulled, so a bad
   tag fails before anything running changes. The non-secret files are staged once as the
   immutable release `/opt/docker/services/<svc>/<rev>/` on the Docker host.
2. **Snapshot.** The host's `verified` revision (the rollback target) and the running revision.
3. **Execute.** `docker compose -p <svc> --project-directory <release> -f - up --wait
   --remove-orphans` over the `docker-dmz` context, with the resolved JSON on stdin. Relative mounts
   (Caddyfile, cloudflared `config.yml`, `local.ini`, `jikan/*`) point into that revision's
   release, so config and compose go live together.
4. **Verify.** [Deployment verification](observability.md#deployment-verification).
5. **Recover or record.** Success writes `verified=<rev>` and prunes releases to the newest five
   plus the verified and previous ones. Failure marks `failed=<rev>`, redeploys the verified
   revision (re-rendered from git; its release still exists), verifies it, and opens
   `revert/<svc>-<rev>`: a PR restoring `compose/<svc>/` to the verified tree so `main` matches
   what runs. `--pending` holds a failed revision until `main` moves. A failed rollback is the
   AGENTS.md §2 hard checkpoint (exit 4); a service with no `verified` revision stops without a
   guess (exit 1).

The label changes with every revision, so any change under `compose/<svc>/` recreates that
project's containers. Secrets cross to the Docker host only on the deploy command's stdin and live
only in the container configuration; no `.env` is written there.

## Where the facts live

| Fact | Where |
|---|---|
| Running revision | `skynet.revision` label on every container (lifted into `inventory/` by the nightly) |
| Last verified / held revision | `/opt/docker/services/<svc>/{verified,failed}` on the Docker host |
| Every write's steps and outcome, refusals included | `/opt/skynet-ops/state/operations.jsonl` on the ops VM; read it with `skynet log` |
| Last `main` the trigger saw, next retry | `/opt/skynet-ops/state/main-seen.json` |

Arcane stays as a read-only dashboard over the same Docker host. Its Git Sync is off and its old
project directories are gone; it never deploys.

## Publishing

A route is declared in git: a vhost block in `compose/caddy-apps/Caddyfile`, and for public reach
a `hostname:` in `compose/cloudflared/config.yml`. Both deploy through the loop above; OpenTofu
derives the internal Technitium record and the public Cloudflare CNAME from them. Authentik's
per-vhost forward-auth objects are not git-shaped, so `skynet publish <svc>` creates them
(additively) once the front door runs `main`, and proves the route. `skynet withdraw <vhost>` is
the gated delete of a removed route's leftovers. Procedures: [`publish-service.md`](../../runbooks/publish-service.md).

## Image pinning & updates

Every `compose.yaml` pins an **exact version tag with digest**. **Renovate** opens weekly batched
PRs with release notes; they deploy through the same loop once merged, and a bad image rolls back
by itself.
