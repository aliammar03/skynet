---
summary: "Restore service data or a guest from a selected recovery point, then reconcile service state with the packaged deploy owner."
trigger: "Restore a service / recover from backup"
tier: "T2; PBS token for VM restore"
executor: "restic, PBS, and skynet deploy service"
rollback: "Stop at the selected restore point; preserve the prior state until verification"
---

# Runbook — restore a service

**Tier:** T2; VM restore needs the PBS token. [`backup.md`](backup.md) covers backup operation and
[`../docs/backup-strategy.md`](../docs/backup-strategy.md) owns policy. **Executor:** restic/PBS for
payload data, then `skynet deploy service` for service configuration and runtime reconciliation.

## Preconditions

- Identify the service/guest, recovery point, paths, configuration branch, and narrowest required
  grant/token. Preserve a current recovery point before replacement where feasible.
- Keep restic/PBS credentials and decrypted service environment values out of commands, output, and
  evidence. The package's default Arcane and age files are restrictive local files.

## Steps

### Restore container data

1. Through an authorized T2 Arcane operation, pause the exact Git Sync and stop its stack. Docker
   context and `svc-ops` SSH inspection are read-only in this runbook; do not use them to stop or
   mutate containers. A separately authorized break-glass write must be documented before any such
   Docker-host mutation.
2. On the affected host under its root grant, source its restic environment, list snapshots, and
   restore only the service paths:

   ```bash
   set -a; . /opt/skynet-ops/secrets/restic-<host>.env; set +a
   restic snapshots
   restic restore <id> --target / \
     --include /opt/docker/appdata/<svc> \
     --include /var/lib/docker/volumes/<svc>_<vol>/_data
   ```

   `--include` prevents replacing unrelated service data. `--tag manual` selects pre-change
   snapshots; `--tag scheduled` selects nightly snapshots.
3. If the recovery point requires historical configuration, represent that configuration on an
   attached local branch containing the matching `compose/<svc>/compose.yaml`, `.env.git`, and
   `.env.sops`. Keep the active checkout's branch history intact; do not restore one file into a
   detached worktree because deployment source identity is a branch head.
4. Through an authorized T2 Arcane operation, re-enable the exact Git Sync before deployment.
   Confirm its repository, branch, `compose/<svc>/compose.yaml` path, `syncDirectory=true`, and
   `autoSync=true`; do not invoke the packaged deploy while the sync is paused.
5. Reconcile the selected configuration with the packaged owner:

   ```bash
   skynet deploy service <svc> --repo <checkout> --branch <branch>
   ```

   The command resolves and reports the exact local 40-hex branch head, pulls that source through the
   exact Arcane sync/project, materializes the environment through SSH stdin, atomically replaces the
   remote `.env` with mode `0600`, redeploys, and requires complete positive Arcane/Docker counts
   with every container running, non-restarting, and healthy. Add `--gate` only for the separate
   report-only P10 route/TLS check. A data restore using current configuration may use the current
   branch instead.
6. Check application-level consistency. For an inconsistent hot database copy,
   add an appropriate dump pre-hook before relying on a filesystem restore.

### Restore a guest

1. With the PBS token, list snapshots and restore the selected guest into `ops-managed`.
2. Boot and verify it. An excluded guest requires an explicit T3 session.

Targeted archive recovery is verified. Full core-node-loss recovery remains unverified; use
[`dr/DR-core-node.md`](dr/DR-core-node.md) when PBS itself is unavailable.

## Verify

- Git Sync is resumed.
- The deploy outcome records the exact source branch/revision/repository and reports
  `verification=runtime-complete` (or the explicit gate result).
- Arcane and Docker show the selected service at that source with equal positive counts and every
  container running, non-restarting, and healthy.
- Application data consistency matches the selected recovery point.

## Rollback

Stop if the point is wrong or verification fails. Preserve the pre-restore data and configuration
for operator recovery; do not layer another restore over it. The deployment command does not
automatically revert a failed restore or gate. If a declarative inverse is required, prepare it with
`skynet rollback service <svc> <deploy-commit> --prepare`, review and human-merge it, then deploy the
merged branch.

## Evidence

Record snapshot ID, source, restored paths, configuration branch/revision, package outcome, health,
and consistency result. Do not record credential values or decrypted environment content.
