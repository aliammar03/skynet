---
summary: "How restic + PBS backups run, and how to trigger one on demand."
trigger: "How do backups work / run a backup"
---

# Runbook — backups (how they run, and how to trigger one)

**Tier:** T2+ (host-level restic/PBS work needs a root grant). **Companion:**
[`restore-service.md`](restore-service.md) for getting data back;
[`../docs/backup-strategy.md`](../docs/backup-strategy.md) for the *why*.

Two layers run on their own timers; you rarely touch them. This runbook covers what they do,
how to stand a new host up, how to force a backup **before you do something risky**, and how to
check they're healthy.

---

## What runs automatically

| Layer | Where | Unit / script | Schedule | Covers |
|---|---|---|---|---|
| **L3 restic → gdrive** | each docker/host | `skynet-restic-backup@<label>` → `backup-restic.sh <label>` | 02:30 +jitter | `/opt/docker/appdata` + `skynet.backup=protect` volumes + any `BACKUP_PATHS` |
| **L5 PBS → gdrive** | `lxc-proxmox-backup-server` | `skynet-pbs-gdrive` → `backup-pbs-gdrive.sh` | 04:00 +jitter | mirrors the whole PBS datastore off-site |

Repos live at `gdrive:Skynet/Backups/{restic/<label>,pbs}`. restic keeps
`--keep-daily 7 --keep-weekly 4 --keep-monthly 6` (auto `forget --prune` + `check` each run).
Secrets are `0600` under `/opt/skynet-ops/secrets/` on each host (`restic-<label>.env`,
`restic-<label>.pass`, `rclone.conf`; PBS: `pbs-gdrive.env`).

L4 (vzdump → PBS) is scheduled inside PBS/Proxmox itself, not here.

---

## Provision a NEW host for restic backups

One command from skynet-ops, inside a root grant to the target (`gr <host>`). Composable —
`--docker` for a docker host, `--path DIR` (repeatable) for any folders, both together:

```bash
scripts/provision-restic.sh <label> root@<ip> --docker                 # docker host
scripts/provision-restic.sh <label> root@<ip> --path /srv/data         # plain host
scripts/provision-restic.sh <label> root@<ip> --docker --path /srv/x --time 03:15
```

It installs restic+rclone, stages secrets `0600`, generates the repo password **on the host**,
deploys `backup-restic.sh`, inits the repo, and enables the nightly timer. **Idempotent** — safe
to re-run (never regenerates the password, never re-inits an existing repo). Afterwards, put the
repo password in the survival kit: `ssh root@<ip> cat /opt/skynet-ops/secrets/restic-<label>.pass`.

---

## On-demand backup — BEFORE something potentially destructive

> "back up docker-dmz before I upgrade it" / "snapshot aiometadata, I'm about to wipe its config"

This is the safety net before a risky change. Tell the agent; it will:

1. **Grant:** if no root grant is active, request the narrowest one (`gr <host>`). You issue it.
2. **Back up now, tagged** so the pre-change snapshot is trivial to find later:
   ```bash
   ssh root@<ip> /opt/skynet-ops/scripts/backup-restic.sh <label> pre-<reason>
   ```
   The snapshot is tagged `manual` + `pre-<reason>` (scheduled runs are tagged `scheduled`).
3. **Report the snapshot ID** — that's your restore point. Then you do the risky thing.
4. **If it goes wrong:** restore that snapshot per `restore-service.md`
   (`restic restore <id>` / find it with `restic snapshots --tag manual`).

Notes:
- restic backups are **incremental + deduplicated**, so an extra on-demand snapshot right before
  a change is cheap and fast (only what changed since the last run uploads).
- For a **guest VM/CT** (not app data), the fast pre-change safety is a **Proxmox snapshot**
  (T2, instant, rollback-able) — `qm/pct snapshot`, see `update-guests.md`. Use a PBS backup
  when you want a durable/off-host copy rather than an in-place snapshot.
- Agent-initiated uploads *can* trip the ops safety guard; if so, run the one-liner above
  yourself (you're already SSH'd into skynet-ops) — it's the same command.

---

## Check backups are healthy

```bash
# restic (per host, inside a grant):
ssh root@<ip> 'set -a; . /opt/skynet-ops/secrets/restic-<label>.env; set +a; \
  restic snapshots; restic check --read-data-subset=2%'

# timers firing?
ssh root@<ip> systemctl list-timers 'skynet-*' --no-pager

# L5 PBS off-site copy (on the PBS host):
ssh root@10.10.20.40 'journalctl -u skynet-pbs-gdrive.service -n 20 --no-pager'
```

The A5 nightly run will fold "last restic/PBS run + snapshot counts" into
`docs/generated/90-backup-status.md` so this becomes a glance, not a command.

---

## Sizing gotcha (don't trust `df`)

The PBS datastore is on an Unraid NFS user-share, so `df` reports the **whole array**, not the
datastore. For the real (deduplicated, on-disk) size — what L5 actually uploads — read PBS's GC
log: `grep -i "on-disk usage" /var/log/proxmox-backup/tasks/*/*garbage_collection*`.
