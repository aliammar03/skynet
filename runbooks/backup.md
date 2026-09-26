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

> **Off-site is failing.** L5 (PBS) is confirmed failing since 2026-08-31 with Google `disabled_client`;
> its last verified sync was 2026-08-22. L3 (docker-dmz restic) failed on 2026-09-26; its cause and
> last success are unknown. Whether older off-site copies can still be restored is unverified. Both
> layers are being replaced, not repaired, by SKY-025 Phase 16. Local PBS backups (L4) still run.

| Layer | Where | Schedule | Covers |
|---|---|---|---|
| L3 restic → gdrive | each Docker/host | `skynet-restic-backup@<label>` at 02:30 + jitter | appdata, protected volumes, `BACKUP_PATHS` |
| L5 PBS → gdrive | PBS host | `skynet-pbs-gdrive` at 04:00 + jitter | whole PBS datastore |

Repos are `gdrive:Skynet/Backups/{restic/<label>,pbs}`. Restic retains 7 daily, 4 weekly, and 6 monthly snapshots, then checks and prunes. L4 vzdump → PBS is scheduled in Proxmox/PBS.

### Installed today (census 2026-09-26, SKY-025 P12)

| Host | Installed | State |
|---|---|---|
| docker-dmz (Debian 13) | `/opt/skynet-ops/scripts/backup-restic.sh` (root, **differs from git**; installed 2026-08-16), `/etc/systemd/system/skynet-restic-backup@.{service,timer}`, instance `docker-dmz`; restic 0.18.0 and rclone 1.60.1 from apt; secrets in `/opt/skynet-ops/secrets` (root `0700`) | timer active; **last run failed** 2026-09-26 02:37 PKT (exit 1 after 7 s). Reading the cause needs root journal access. |
| PBS CT 240 (10.10.20.40, Debian 13, PBS 4.2.5) | `/opt/skynet-ops/scripts/backup-pbs-gdrive.sh` (matches git apart from one comment line), `/etc/systemd/system/skynet-pbs-gdrive.{service,timer}` (identical to `scripts/systemd/`), timer 04:00; rclone 1.60.1; secrets `pbs-gdrive.env` and `rclone.conf` in `/opt/skynet-ops/secrets` (root `0700`); datastore `unraid` = NFS `10.10.20.20:/mnt/user/pbs-backups` at `/mnt/datastore/unraid` | **L5 is down.** Every run since 2026-08-31 fails: Google returns `disabled_client` ("The OAuth client was disabled") for the `gdrive` remote's custom `client_id`. The last verified sync was 2026-08-22 (0 differences). The host was also down from 2026-09-16 13:49 to 2026-09-26 17:17 PKT. |

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
