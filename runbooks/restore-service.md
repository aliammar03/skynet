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
  evidence. The package's age key and optional Arcane migration credential are restrictive local files.

## Steps

### Restore container data

1. Through an authorized T2 Arcane operation, keep `autoSync=false` for the exact Git Sync. If this
   is the first handoff from legacy auto-sync, disable it while old source and environment still
   agree; verify the deployed Arcane maximum sync duration and wait at least that long, never less
   than five minutes, then confirm the expected old revision and runtime before continuing. The
   setting cannot cancel an admitted sync. Stop the exact stack through Arcane. Docker context and
   `svc-ops` SSH inspection are read-only in this runbook; do not use them to stop or mutate
   containers. A separately authorized break-glass write must be documented before any such
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
3. If the recovery point needs historical configuration, use an attached local branch whose
   head contains the matching `compose/<svc>/compose.yaml`, `.env.git`, `.env.sops`, and relative
   runtime files. Keep the current branch history intact; the full branch-head Git revision is the
   authored generation identity.
4. Check `skynet deploy status <svc>` and any legacy Arcane sync. Enabled auto-sync is a pre-write
   refusal; disable/drain it while old source and environment agree, then verify old running
   revision before first generation takeover. A disabled record can remain.
5. Reconcile configuration with the packaged owner:

   ```bash
   skynet deploy service <svc> --repo <checkout> --branch <branch>
   ```

   The command prepares a complete immutable generation from the selected exact Git revision,
   streams effective `.env` by SSH stdin into the protected remote generation at mode `0600`,
   activates directly through Docker Compose, and requires independent complete container/health
   and DMZ route/TLS verification before stable promotion. A data restore using current
   configuration may select the current branch. A failed candidate does not erase the prior
   stable rollback candidate.
6. Check application-level consistency. For an inconsistent hot database copy,
   add an appropriate dump pre-hook before relying on a filesystem restore.

### Restore a guest

1. With the PBS token, list snapshots and restore the selected guest into `ops-managed`.
2. Boot and verify it. An excluded guest requires an explicit T3 session.

Targeted archive recovery is verified. Full core-node-loss recovery remains unverified; use
[`dr/DR-core-node.md`](dr/DR-core-node.md) when PBS itself is unavailable.

## Verify

- `skynet deploy status` reconciles state pointers and Docker generation labels to one complete
  running generation; old `stable` remains available until the new generation is verified.
- The deploy outcome records the exact full Git revision and independent health/route result.
- Application data consistency matches the selected recovery point.

## Rollback

Stop if the point is wrong or verification fails. Preserve pre-restore payload data and the retained
stable generation. Use `skynet rollback service <svc> [--to <retained-full-revision>] --apply` only
under an explicit runtime rollback plan; the command independently verifies before promotion and
does not edit Git. Correct authored source separately with a normal reviewed PR.

## Evidence

Record snapshot ID, source, restored paths, configuration branch/revision, package outcome, health,
and consistency result. Do not record credential values or decrypted environment content.
