---
summary: "Restore a service or VM from restic/PBS using a selected recovery point."
trigger: "Restore a service / recover from backup"
tier: "T2; PBS token for VM restore"
executor: "restic, PBS, and scripts/gitops-deploy.sh"
rollback: "Stop at the selected restore point; preserve the prior state until verification"
---

# Runbook — restore a service

**Tier:** T2; VM restore needs the PBS token. [`backup.md`](backup.md) covers backup operation and [`../docs/backup-strategy.md`](../docs/backup-strategy.md) owns policy.

## Preconditions

- Identify the service/guest, restore point, paths, and necessary grant/token. Preserve a current recovery point before replacement where feasible.

## Steps

### Restore container data

1. Pause the Arcane Git Sync for the project, then stop its stack through Arcane (or the Docker context).
2. On the affected host under its root grant, source its restic environment, list snapshots, and restore only the service paths:
   ```bash
   set -a; . /opt/skynet-ops/secrets/restic-<host>.env; set +a
   restic snapshots
   restic restore <id> --target / \
     --include /opt/docker/appdata/<svc> \
     --include /var/lib/docker/volumes/<svc>_<vol>/_data
   ```
   `--include` prevents replacing unrelated service data. `--tag manual` selects pre-change snapshots; `--tag scheduled` selects nightly snapshots.
3. Restore configuration for that point only when required, then redeploy:
   ```bash
   git checkout <commit> -- compose/<svc>/.env.sops
   scripts/gitops-deploy.sh <svc>
   ```
   The deploy script materializes `.env.git` plus decrypted `.env.sops`, deploys, and checks health. A restore to current configuration can omit the checkout.
4. Re-enable Git Sync and check application-level consistency. For an inconsistent hot database copy, add an appropriate dump pre-hook before relying on filesystem restore.

### Restore a guest

1. With the PBS token, list snapshots and restore the selected guest into `ops-managed`.
2. Boot and verify it. An excluded guest requires an explicit T3 session.

The Drive→scratch-PBS path and CT 101 archive reconstruction were proven on 2026-08-16. A full core-node-loss drill has not run; use [`dr/DR-core-node.md`](dr/DR-core-node.md) when PBS itself is unavailable.

### Known service note

- **aiometadata:** raw restic recovery of SQLite plus the protected Mongo volume was witnessed consistent on 2026-08-16; `scripts/gitops-deploy.sh aiometadata` returned all six containers healthy. Add a dump pre-hook if its write load later makes hot-copy recovery unsafe.

## Verify

- Git Sync is resumed; service/guest health and application data consistency match the selected restore point.

## Rollback

- Stop if the point is wrong or verification fails. Preserve the pre-restore state for operator recovery; do not layer another restore over it.

## Evidence

- Record snapshot ID, source, restored paths, configuration commit, health, and consistency result.
