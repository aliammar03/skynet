---
summary: "Deploy or update one Compose service with the packaged Arcane GitOps owner and complete runtime reconciliation."
trigger: "Deploy or update a service"
tier: "T2 PR-gated"
executor: "skynet deploy service, Arcane Git Sync, and optional skynet verify deployment"
rollback: "skynet rollback service <service> <deploy-commit> --prepare, then review and human-merge"
---

# Runbook — deploy / update a service

**Tier:** T2 (PR-gated). **Executor:** `skynet deploy service` + Arcane Git Sync. **Rollback:**
prepare a reviewed inverse with `skynet rollback service`; the command never pushes, merges, or
automatically rolls back.

## Preconditions

- Identify the service, persistent data, intended ingress, and whether encrypted configuration is
  needed.
- The Compose change is on a branch that follows the PR and human-merge policy. The operator has
  the scoped Arcane credential file (default `/opt/skynet-ops/secrets/arcane.env`) and local age key
  (default `/opt/skynet-ops/secrets/age.key`). Never print either or any decrypted value.
- `compose/<service>/compose.yaml` is present, digest-pins every image, declares `env_file: .env`,
  has a healthcheck for every container, and keeps non-secret defaults in `.env.git` and secrets in
  `.env.sops`.
- Before any source/environment-coupled revision is merged or exposed, migrate a legacy sync with
  `autoSync=true` through the T2 Arcane interface: set `autoSync=false` while the old source and old
  environment still agree. Verify the deployed Arcane version's maximum sync duration and wait at
  least that long, never less than five minutes, then confirm that the project remains on the
  expected old revision and its expected runtime. Disabling the control does not cancel an admitted
  run. If the duration or old source/runtime cannot be verified, do not merge/expose the revision.
  This one-time change uses no T3 access.

## Steps

### Apply the service standard

Use the Compose rules in [`../docs/conventions/compose.md`](../docs/conventions/compose.md). Validate
the manifest locally with a dummy environment in a disposable checkout; do not commit plaintext
`.env`.

### Deploy with the packaged owner

Run from the checkout whose local branch should be reconciled:

```bash
skynet deploy service <service> [--repo <checkout>] [--branch <branch>] \
  [--credentials-file <file>] [--age-key <file>] [--environment-id <id>] \
  [--timeout <1..300>] [--no-deploy] [--gate] [--json]
```

The default checkout is the current directory. Without `--branch`, the command uses
`GITOPS_BRANCH` when set, otherwise `main`. Before writing to Arcane it resolves the exact local
`refs/heads/<branch>` commit and reports the lowercase 40-hex `source.revision`, `source.branch`,
and normalized Git `source.repository`. Keep that identity with the deployment evidence; do not
substitute a short SHA, remote label, or a later branch head.

Before any Arcane write, the command binds `compose.yaml`, `.env.git`, and optional `.env.sops`
content and executable modes to blobs in that selected commit. It fails closed if a selected input
is missing from the worktree or differs in content or mode, if an extra local service input is
present, or if any input is a symlink or not a regular file.

The command then selects exactly one matching Arcane repository, existing service sync, and project.
The sync must point to `compose/<service>/compose.yaml`, the matching repository, and have
`syncDirectory=true` plus `autoSync=false`. These are preconditions: the command does not toggle
scheduled sync. A missing sync or project is refused because this path cannot safely bootstrap a
first activation.

The package first materializes the effective environment from the bound `.env.git` and optional
`.env.sops` bytes: sops decrypts the selected encrypted bytes via stdin locally with
`SOPS_AGE_KEY_FILE`, and plaintext crosses to the off-host project only through SSH stdin. A pinned
writer replaces the exact project `.env` atomically, preserving the observed project owner and mode
`0600`. No plaintext temporary file, argument, report, or transcript is used. Only after this write
does normal deployment repoint the sync, if needed, and request its manual source sync. Arcane may
redeploy an already-running project during that sync. The command always follows with an explicit
bounded redeploy so environment-only changes are applied as well.

Manual source sync may redeploy a running project. The command's explicit redeploy consumes
Arcane's bounded NDJSON stream and requires its terminal `done=true` success frame. Malformed,
failed, or incomplete streams fail closed; progress frames and response bodies are not exposed. It
then waits for the project to report `running` with equal positive service/running counts and
inspects the exact Compose project over unprivileged SSH: the container set must be non-empty and
count-equal, every container must be running, not restarting, and report `Health.Status=healthy`. A
missing healthcheck is failure. For `cloudflared`, only the reconciled project container IDs are
restarted, then the same Arcane/runtime checks and unchanged ID set are required.

`--no-deploy` stops after atomically preparing the selected environment. It does not repoint the
source branch, manually sync source, request a redeploy, or verify runtime. Its verification is
`environment-prepared; source-not-activated (--no-deploy)`. Treat it as intermediate preparation;
do not manually sync/redeploy the project before a normal packaged deployment completes.

### Optional P10 report-only gate

Add `--gate` only when the separate P10 verification is wanted. After runtime reconciliation it runs
`skynet verify deployment <service> <full-revision>` using the read-only `docker-dmz` context. The
gate checks exact Arcane/project revision identity, complete equal project/Docker counts, all
container health, and every declared route from the `dmz` network with verified TLS. It accepts HTTP
100–499, including 302/401; an undeclared route is `skipped`. It never deploys, restarts, edits Git,
or rolls back. A gate failure leaves the healthy runtime in place and is reported as no automatic
rollback.

The result is truthful structured evidence. With `--json`, retain `status`, `source`,
`completed_steps`, `verification`, `recovery`, `reason` when present, and non-secret `detail` fields.
Branch repoint uses at most three bounded attempts; ambiguous branch-repoint writes are reread and
reconciled before a retry. A manual source-sync POST is single-admission because Arcane exposes only
the last completed sync result, not an operation identity or in-flight lease. If the request/response
is ambiguous, or completion remains non-terminal through the deadline, the command issues no second
POST and reports explicit inspect-before-retry recovery. Only a normally returned POST followed by
positively newer terminal `failed`/`error` evidence permits a bounded source-sync retry. If
`completed_steps` contains `source-synced`, recovery says source activation occurred even when a
later consistency, redeploy, runtime, or gate check fails. The command never implies that Arcane or a
failed gate reverted the service.

## Verify

- `skynet deploy service` reports success with `verification=runtime-complete`, or
  `runtime-complete-and-gate-passed` when `--gate` was selected.
- The source fields identify the exact local branch head and repository.
- Arcane and Docker show one matching project at that revision, with complete positive counts and
  every container running, non-restarting, and healthy.
- If the service declares ingress, the optional gate records each route result and TLS verification.

## Rollback

If deployment or the optional gate fails, inspect the exact project and outcome first. Prepare a
reviewable inverse for the authored deployment commit (a separate identity from the verifier's
expected revision):

```bash
skynet rollback service <service> <deploy-commit> --prepare --repo <checkout>
```

Rollback without `--prepare` is report-only validation. Preparation refuses protected constitutional
or gate paths, commits that do not touch the selected service, mixed Compose projects, and unsafe
changed-path observations. It creates a unique local `rollback/<service>-<first-12-hex-of-revision>`
branch from the attached base, creates a revert
commit in a temporary isolated worktree, and cleans that worktree. Conflicts retain the worktree for
manual resolution. Nothing is pushed or merged; review
and human-merge the branch, then run `skynet deploy service` against the merged branch so Arcane
converges.

The retained `scripts/gitops-deploy.sh` and `scripts/gitops-rollback.sh` commands are temporary
compatibility forwarders to these packaged commands for P22 removal.

## Evidence

Record the package outcome (including source identity, completed steps, verification, recovery, and
any reason), the Compose PR, persistent-data impact, and any refreshed inventory. Do not record
credential values or decrypted environment content.
