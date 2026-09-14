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

The command then selects exactly one matching Arcane repository, service sync, and project. The sync
must point to `compose/<service>/compose.yaml`, the selected branch, and the matching repository;
`syncDirectory` and `autoSync` must both be true. A missing sync is created with the bounded default
interval; an existing sync is only repointed when its branch differs. Missing, duplicate, malformed,
or mismatched identities fail closed.

The selected source is pulled until Arcane reports the exact branch head. The package materializes
the effective environment from `.env.git` and optional `.env.sops`: sops decrypts locally with
`SOPS_AGE_KEY_FILE`, and plaintext crosses to the off-host project only through SSH stdin. A pinned
writer replaces the exact project `.env` atomically, preserving the observed project owner and mode
`0600`. No plaintext temporary file, argument, report, or transcript is used.

Normal deployment requests a redeploy and waits for the project to report `running` with equal
positive service/running counts. It then inspects the exact Compose project over unprivileged SSH:
the container set must be non-empty and count-equal, every container must be running, not restarting,
and report `Health.Status=healthy`. A missing healthcheck is failure. For `cloudflared`, only the
reconciled project container IDs are restarted, then the same Arcane/runtime checks and unchanged ID
set are required.

Use `--no-deploy` only when source sync and environment replacement are the intended scope. Its
success means `source-and-environment-only (--no-deploy)`, not a healthy runtime.

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
Sync creation, branch repoint, and source pull use at most three bounded attempts; ambiguous writes
are reread and reconciled before retry. A failed/ambiguous outcome identifies what completed and what
must be inspected before retrying. The command never implies that Arcane or a failed gate reverted
the service.

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
