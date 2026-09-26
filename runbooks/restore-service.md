---
summary: "Restore a service or VM from restic/PBS using a selected recovery point."
trigger: "Restore a service / recover from backup"
tier: "T2; PBS token for VM restore"
executor: "restic, PBS, and skynet deploy"
rollback: "Stop at the selected restore point; preserve the prior state until verification"
---

# Runbook — restore a service

**Tier:** T2; VM restore needs the PBS token. [`backup.md`](backup.md) covers backup operation and [`../docs/backup-strategy.md`](../docs/backup-strategy.md) owns policy.

## Preconditions

- Identify the service/guest, restore point, paths, and necessary grant/token. Preserve a current recovery point before replacement where feasible.

## Steps

### Restore container data

1. Stop the stack: `docker --context docker-dmz compose -p <svc> stop`. The deploy timer leaves a
   stopped project alone while `main` still names its running revision.
2. On the affected host under its root grant, source its restic environment, list snapshots, and restore only the service paths:
   ```bash
   set -a; . /opt/skynet-ops/secrets/restic-<host>.env; set +a
   restic snapshots
   restic restore <id> --target / \
     --include /opt/docker/appdata/<svc> \
     --include /var/lib/docker/volumes/<svc>_<vol>/_data
   ```
   `--include` prevents replacing unrelated service data. `--tag manual` selects pre-change snapshots; `--tag scheduled` selects nightly snapshots.
3. Redeploy. For the current configuration: `skynet deploy <svc>`. For the configuration at the
   restore point (a merged commit): `skynet deploy <svc> --revision <commit>` — its `.env.git` and
   `.env.sops` travel with it. Then open a PR restoring `compose/<svc>/` on `main` to that tree, or
   the timer will move the service forward again to `main`'s revision.
4. Check application-level consistency. For an inconsistent hot database copy, add an appropriate dump pre-hook before relying on filesystem restore.

### Restore a guest

1. With the PBS token, list snapshots and restore the selected guest into `ops-managed`.
2. Boot and verify it. An excluded guest requires an explicit T3 session.

Targeted archive recovery is verified. Full core-node-loss recovery remains unverified; use
[`dr/DR-core-node.md`](dr/DR-core-node.md) when PBS itself is unavailable.

## Verify

- Git Sync is resumed; service/guest health and application data consistency match the selected restore point.

## Rollback

- Stop if the point is wrong or verification fails. Preserve the pre-restore state for operator recovery; do not layer another restore over it.

## Evidence

- Record snapshot ID, source, restored paths, configuration commit, health, and consistency result.
