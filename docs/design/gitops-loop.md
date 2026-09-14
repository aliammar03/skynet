---
summary: "The packaged Arcane GitOps deploy/rollback loop, source identity, health contract, and recovery boundaries."
---

# Spoke · The GitOps loop

> How a reviewed service change becomes a running container, and how an operator prepares a
> reviewable recovery. Governed by [`../system-design.md`](../system-design.md) and the Compose
> rules in [`../conventions/compose.md`](../conventions/compose.md).

## The truth model

Two private GitHub repositories carry operational truth:

- **`skynet`** — `AGENTS.md`, `.sops.yaml`, `docs/`, `inventory/` (generated; never hand-edited),
  `compose/<service>/`, retained procedures, runbooks, and operator entry points.
- **`skynet-opnsense`** — the OPNsense `os-git-backup` mirror. Its `config.xml` is disaster-recovery
  material, not the live firewall inventory source.

## The loop

```
edit compose/<service>/ → branch → PR → Ali merges
   → `skynet deploy service <service>` selects one local branch head
   → Arcane Git Sync reconciles the exact source and project
   → complete Arcane/Docker runtime health
   → optional `--gate` runs the separate P10 report-only route verifier
   → agent records the outcome and refreshes inventory when requested
```

The installed package owns deployment and rollback procedures. The retained
[`gitops-deploy.sh`](../../scripts/gitops-deploy.sh) and
[`gitops-rollback.sh`](../../scripts/gitops-rollback.sh) names are temporary compatibility
forwarders to the package and are scheduled for removal in P22; they are not separate owners.

## Packaged deployment contract

Invoke:

```bash
skynet deploy service <service> [--repo <checkout>] [--branch <branch>]
  [--credentials-file <file>] [--age-key <file>] [--environment-id <id>]
  [--timeout <1..300>] [--no-deploy] [--gate] [--json]
```

The default checkout is the current directory. The branch is `GITOPS_BRANCH` when set, otherwise
`main`; `--branch` is explicit. Before any Arcane write, the package resolves exactly
`refs/heads/<branch>^{commit}` to a lowercase 40-hex commit and normalizes the checkout's Git
origin to the reported `source.repository`. The structured outcome always carries
`source.branch`, `source.revision`, and `source.repository`; retain these fields as the source
identity for the operation.

The Arcane write contract is exact and unique:

- the normalized origin matches exactly one repository returned by
  `/api/customize/git-repositories`;
- the selected environment (credential `ARCANE_ENV_ID`, `--environment-id`, or `0`) has exactly
  one sync for the service, with matching `name`, `projectName`, `repositoryId`, `branch`, and
  `composePath=compose/<service>/compose.yaml`;
- the sync must have `syncDirectory=true` and `autoSync=true`; a missing sync is created with
  `syncInterval=180`, while an existing sync is only repointed when its branch differs;
- the sync pull must report `lastSyncStatus=success` and the exact selected commit; the bound
  project must report `gitOpsManagedBy=<sync-id>`, that same `lastSyncCommit`, path
  `/opt/docker/arcane-projects/<service>`, and a positive `serviceCount`.

Duplicate, missing, malformed, mixed, or mismatched repository/sync/project identities fail closed.
The Arcane API uses the literal `ARCANE_URL`/`ARCANE_TOKEN` assignments in
`/opt/skynet-ops/secrets/arcane.env` and the established `X-API-Key` header (an alternate header is
refused). HTTPS uses the default verifying TLS context and redirects are rejected. The remote Docker
host is the Arcane URL hostname reached as `svc-ops`; the deploy path does not grant root.

## Environment and runtime reconciliation

The package reads regular, non-symlink `.env.git` and optional `.env.sops` files from the selected
checkout. It runs `sops -d` locally with `SOPS_AGE_KEY_FILE` set to the local age-key path, then
sends the effective bytes to the host only through the SSH process's stdin. Plaintext is not written
to a local temporary file, command argument, or report. On the exact Arcane project path, a pinned
BusyBox writer creates a same-directory temporary file, applies the observed project UID:GID,
sets mode `0600`, and atomically renames it to `.env`; an owner or path mismatch is refused.

After environment replacement, normal deployment requests the exact project redeploy and waits for
`status=running` with `runningCount=serviceCount`. It then observes the exact Compose project label
over SSH: the container set must be non-empty and count-equal, every container must be
`Running=true`, `Restarting=false`, and report `Health.Status=healthy`. Missing health is failure,
not success. `--no-deploy` stops after source sync and environment replacement and reports
`verification=source-and-environment-only (--no-deploy)`; it does not claim runtime health.

`cloudflared` has one additional bounded action: after count reconciliation, the package restarts
only the exact container IDs returned for that Compose project, then repeats Arcane/runtime health
and requires the same ID set. It never restarts unrelated containers.

Sync create, branch repoint, and source pull each use at most three bounded attempts. Ambiguous
writes are reconciled by rereading the exact repository/sync/project state before a retry. A final
ambiguous or failed write is reported as such; the package never claims success from a request alone.
Each result reports `status`, completed steps, `verification`, and `recovery`. A runtime or gate
failure remains a failed operation with explicit inspect-before-retry guidance; no automatic
authored revert, destroy, or rollback is attempted.

## The separate P10 gate

`--gate` is opt-in after runtime reconciliation. It invokes the packaged, report-only
`skynet verify deployment <service> <full-revision>` path using the read-only `docker-dmz` context.
That verifier independently checks exact Arcane/project revision identity, positive equal project
and Docker counts, all container health, and every declared `aliammar.net` route from the `dmz`
network with verified TLS. A route may return any HTTP status from 100 through 499, including 302 or
401; an undeclared route is explicitly skipped. The gate never deploys, restarts, edits Git, or
rolls back. A gate failure after a healthy runtime leaves the runtime in place and reports
`no automatic rollback performed`.

## Recovery and rollback

Rollback is report-only by default:

```bash
skynet rollback service <service> <deploy-commit> [--repo <checkout>] [--timeout <1..300>] [--json]
```

The command validates a lowercase full 40-hex commit, its presence and ancestry on the attached
base branch, and the complete inverse scope. It refuses unsafe paths, protected constitutional or
gate paths, commits that do not touch `compose/<service>/`, and commits mixing another Compose
project (the sole publication exception is the matching `compose/caddy-apps/Caddyfile`). A report
returns `status=report-only` and tells the operator the unique branch name
`rollback/<service>-<first-12-hex-of-revision>`; it does not mutate Git, Arcane, or the host.

For an explicit isolated preparation, add `--prepare`:

```bash
skynet rollback service <service> <deploy-commit> --prepare
```

The package creates a temporary worktree from the attached base branch, creates a revert commit
(mainline `-m 1` for a merge commit), removes the worktree, and leaves the review branch local.
Conflicts retain the worktree for manual resolution; cleanup failure is reported with its path.
Nothing is pushed or merged. Review and human-merge the branch, then run
`skynet deploy service <service>` against the merged branch so Arcane converges. Arcane is a
reconciler, not a rollback executor.

## Image updates

Every `compose.yaml` carries an image tag plus an immutable digest; Renovate proposes pin changes
through PRs. Arcane's auto-update polling remains off for Git-synced projects. Deploy and rollback
commands do not create Git/release tags or perform image updates outside the reviewed Compose
revision.
