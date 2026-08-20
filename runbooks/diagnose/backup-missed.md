---
summary: "Triage a missed backup — check the timer, the last snapshot age, and repo reachability across restic→gdrive and PBS→gdrive, fix the timer/creds/repo declaratively."
trigger: "An expected backup/snapshot is missing / a restic or PBS timer failed"
tokens: 745
---

# Diagnose — backup missed

**Trigger:** an expected snapshot is absent, a `restic`/PBS timer is `failed`/inactive, or a restore
attempt finds the latest backup too old.
**Tier:** **T1** to read timers, unit logs, and last-snapshot age. Reading a restic repo needs its
password (sops/0600 secret) — the **operate token / a narrowest grant**, never plaintext. Fix routes to
timer + backup config in git. Background: [[skynet-backups]] and [`backup.md`](../backup.md).

> **Diagnose imperatively, fix declaratively.** A missed backup is usually a *timer* or a *credential*,
> both of which live in git/sops — fix them there, not with a one-off manual run that hides the cause. (SKY-005.)

## 1. Confirm — is the timer even firing?

```bash
scripts/recon.sh <host>                                  # failed units surface here first
systemctl list-timers --all | grep -Ei 'restic|pbs|backup'
systemctl status  <backup>.service --no-pager -n 20
journalctl -u <backup>.service -n 80 --no-pager
```

## 2. Check the repo / last snapshot

```bash
# restic (repo + password come from the sops/0600 secret — sourced, never echoed)
restic snapshots --latest 3          # how old is the newest? which paths?
# PBS: last backup timestamp per guest via the T1 read token / PBS UI
rclone lsd <gdrive-remote>: 2>&1 | head   # is the off-site remote even reachable?
```

| Signal | Cause | Fix routes to |
|---|---|---|
| timer `inactive`/`dead` | disabled or never enabled | the timer unit in the host's config module |
| service `failed`, log shows repo lock | a prior run died mid-flight | `restic unlock` (once), then find why it died |
| `Fatal: unable to open repository` | gdrive/rclone token expired, or network | the rclone remote's credential (sops) |
| runs green, but 0 files / wrong paths | source path moved | the backup job's path config |
| snapshots exist but old | timer fired but errored silently every night | read older journal entries for the pattern |

## 3. Fix declaratively

- **Disabled/misfiring timer** → correct the `.timer`/`.service` in the host's config module → PR.
- **Expired credential** → re-encrypt the secret into `.env.sops` / place `0600` under
  `/opt/skynet-ops/secrets/` — **never** commit it plaintext.
- **Repo lock** → `restic unlock` is the one sanctioned imperative step; still record *why* it locked.

Confirm the *next* scheduled run succeeds — a backup you can't restore from is not a backup
([`restore-service.md`](../restore-service.md)).

## 4. Record

`bin/new journal incident "<host> backup missed — <timer|creds|repo>"` — last good snapshot age, the unit
error, and the config/secret PR that fixed it. ([journal](../../journal/README.md).)
