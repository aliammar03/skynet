---
summary: "Deploy one exact reviewed Compose revision as an immutable Skynet generation and promote only after independent verification."
trigger: "Deploy or update a service"
tier: "Supervised T2 PR-gated"
executor: "skynet deploy prepare/service/status and direct svc-ops Docker Compose"
rollback: "skynet rollback service <service> [--to <full-revision>] --apply; then reviewed authored-source correction"
---

# Runbook — deploy / update a service

**Tier:** supervised T2, PR-gated. The operator plans the intended service/revision, Docker host,
and retained stable rollback generation before a live write; approval covers that stated scope.
The packaged command performs preparation, activation, and verification without per-command approval.

## Preconditions

- The Compose change has followed the normal PR and human-merge policy. Select an exact local
  branch-head commit; a dirty worktree is not release input.
- `compose/<service>/compose.yaml` declares digest-pinned images, `env_file: .env`, and a real
  healthcheck for each required container. `.env.git` contains non-secret defaults; optional
  `.env.sops` contains encrypted secrets. Keep the age key local and never print credentials or
  decrypted values.
- The documented standing `svc-ops` Docker-host SSH path must provide Docker Compose and access to
  its persistent protected state. No new Docker/root grant is implied.
- Inspect any Arcane Git Sync for this service. If `autoSync=true`, disable it through the existing
  T2 Arcane interface **while old source and old environment still agree**. Verify the deployed
  maximum sync duration, wait at least that duration and never less than five minutes, then confirm
  the currently running old revision and container/route state. Disabling auto-sync does not cancel
  a run already admitted. If drain duration or old runtime revision cannot be proved, stop before
  direct activation. A disabled legacy sync can remain as observational metadata.

For a service's first Skynet takeover, record that non-secret evidence in a bounded JSON file. The
old service list comes from Compose at the exact old revision and must match the running containers'
Compose service labels. This lets `svc-ops` prove a complete legacy project without gaining access to
Arcane's protected source directory.

```json
{
  "schema": 1,
  "service": "<service>",
  "sync_present": true,
  "auto_sync_disabled": true,
  "drained": true,
  "old_revision": "<full-old-revision>",
  "old_runtime_verified": true,
  "legacy_working_dir": "/opt/docker/arcane-projects/<service>",
  "old_services": ["<compose-service>"],
  "recorded_at": "<UTC timestamp>"
}
```

The file contains identities and booleans only. Do not put environment values, credentials, request
bodies, or probe response bodies in it. A new project with no Arcane sync and no existing containers
does not need migration evidence.

## Prepare and deploy

```bash
skynet deploy prepare <service> [--repo <checkout>] [--branch <branch>] [--json]
skynet deploy status <service> [--json]
skynet deploy service <service> [--repo <checkout>] [--branch <branch>] \
  [--migration-evidence <non-secret-json>] [--json]
```

`prepare` reads only Git objects at one full branch-head revision and atomically publishes a complete
valid immutable generation. It streams the layered effective environment from local memory through
SSH stdin to a protected remote `.env` at mode `0600`; it never activates containers. Preparing the
same revision again verifies and reuses the retained generation. Committed regular files retain
deterministic Git semantics (`100644` → `0644`, `100755` → `0755`) and runtime directories are `0755`;
any retained byte or mode drift is a conflict.

`service` prepares, locks and reconciles the actual Docker project, checks Arcane scheduling, activates
from the selected generation with the stable project name, independently verifies the exact generation,
complete running healthy containers, and declared `dmz`/TLS/HTTP routes, then promotes `stable`.
Successful Docker Compose application alone is not deployment success.

If transport times out, status is unresolved: check whether the previous lock remains held, inspect
runtime labels and operation evidence after it releases, and resume only the **same** generation if
safe. A partial or mixed project requires recovery before any different-generation deployment.
A failed candidate may remain `active` while old `stable` remains the explicit rollback candidate.
There is no automatic rollback in P11.

## Verify and recover

```bash
skynet deploy status <service> [--json]
skynet verify deployment <service> <full-revision> [--json]
skynet rollback service <service> [--to <retained-full-revision>]       # report only
skynet rollback service <service> [--to <retained-full-revision>] --apply
```

`verify deployment` is read-only except its bounded ephemeral route probe container. It reads route
and Compose address declarations from the expected Git revision rather than checkout bytes, and checks the
release manifest, Docker Compose project and generation labels, exact complete service set, all
required running healthy containers, and canonical declared routes from the `dmz` ingress vantage
with verifying TLS. An undeclared route is recorded as skipped. Arcane is optional UI observation.

Rollback requires a retained generation identity (or one unambiguous `previous` candidate). With
`--apply`, the exact historical commit must exist locally; Skynet reconstructs that commit's complete
service tree and effective environment and directly compares retained bytes, modes, and manifest
before any Compose mutation. It then activates through the same locked Compose/verification path and
promotes only if verification succeeds.
It does not create a branch, commit, push, merge, or modify authored source. Report runtime/Git
divergence and correct source by a separate normal reviewed PR. Record the operation and raw evidence
in `journal/`; refresh generated inventory through its normal collector when needed.
