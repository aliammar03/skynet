---
summary: "How restic and PBS backups run, how to provision restic, and how to take a pre-change backup."
trigger: "How do backups work / run a backup"
tier: "T2+ root grant"
executor: "scripts/provision-restic.sh and backup-restic.sh"
rollback: "Restore with restore-service.md"
---

# Runbook — backups

**Tier:** T2+ root grant for host actions. [`restore-service.md`](restore-service.md) restores data; [`../docs/backup-strategy.md`](../docs/backup-strategy.md) owns policy.

## Preconditions

- Obtain the narrowest required root grant. Status inspection is T1.

## Steps

### Automatic layers

| Layer | Where | Schedule | Covers |
|---|---|---|---|
| L3 restic → gdrive | each Docker/host | `skynet-restic-backup@<label>` at 02:30 + jitter | appdata, protected volumes, `BACKUP_PATHS` |
| L5 PBS → gdrive | PBS host | `skynet-pbs-gdrive` at 04:00 + jitter | whole PBS datastore |

Repos are `gdrive:Skynet/Backups/{restic/<label>,pbs}`. Restic retains 7 daily, 4 weekly, and 6 monthly snapshots, then checks and prunes. L4 vzdump → PBS is scheduled in Proxmox/PBS.

### Installed today (census 2026-09-26, SKY-025 P12)

| Host | Installed | State |
|---|---|---|
| docker-dmz (Debian 13) | `/opt/skynet-ops/scripts/backup-restic.sh` (root, **differs from git**; installed 2026-08-16), `/etc/systemd/system/skynet-restic-backup@.{service,timer}`, instance `docker-dmz`; restic 0.18.0 and rclone 1.60.1 from apt; secrets in `/opt/skynet-ops/secrets` (root `0700`) | timer active; **last run failed** 2026-09-26 02:37 PKT (exit 1 after 7 s). Reading the cause needs root journal access. |
| PBS CT 240 (10.10.20.40) | `skynet-pbs-gdrive.{service,timer}` → `/opt/skynet-ops/scripts/backup-pbs-gdrive.sh` per `scripts/systemd/` | **not observed.** The ops VM has no pinned host key or standing SSH path; the census needs a grant. |

The ops VM runs no backup unit. Its only timer is `skynet-nightly`.

### Provision restic on a host

Run inside a root grant:

```bash
scripts/provision-restic.sh <label> root@<ip> --docker
scripts/provision-restic.sh <label> root@<ip> --path /srv/data --time 03:15
```

The idempotent script stages restrictive secrets, deploys and enables the timer, initializes only a new repository, and creates the repository password on the host. Save that password to the survival kit.

### Take a pre-change backup

1. Request the host grant if needed.
2. Run `ssh root@<ip> /opt/skynet-ops/scripts/backup-restic.sh <label> pre-<reason>`.
3. Record the returned snapshot ID before making the risky change; restore it with `restore-service.md` if needed.

For a guest configuration change, use a Proxmox snapshot for fast rollback; use PBS for a durable off-host copy.

## Verify

```bash
ssh root@<ip> 'set -a; . /opt/skynet-ops/secrets/restic-<label>.env; set +a; restic snapshots; restic check --read-data-subset=2%'
ssh root@<ip> systemctl list-timers 'skynet-*' --no-pager
ssh root@10.10.20.40 'journalctl -u skynet-pbs-gdrive.service -n 20 --no-pager'
```

For actual PBS datastore use (not the Unraid share’s `df`), inspect PBS GC logs for `on-disk usage`.

## Rollback

- Backups are additive. Restore the selected snapshot; do not delete backup data during recovery.

## Evidence

- Record snapshot ID, host, tag, and timer/health result in the job report or journal.
