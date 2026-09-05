---
summary: "Triage a full disk (or exhausted inodes) — find what ate the space, distinguish data vs logs vs docker cruft, fix the cause declaratively."
trigger: "Disk full / write failures / df at 100% (or inodes exhausted with space free)"
tier: "T1/T2+"
executor: "host inspection; approved host remediation when needed"
rollback: "restore retained data or revert the declarative capacity fix"
---

# Diagnose — disk full

**Tier:** **T1/T2+** (read-only diagnosis; emergency cleanup or disk resize needs the narrowest grant).
**Trigger:** recon's *Disk* section shows a filesystem near 100%, write failures, or inodes exhausted
while space looks free.

## Preconditions

- Have the affected host and full mount; start with read-only usage inspection.
- Any deletion, cleanup, or disk resize requires the narrowest host and shortest grant. Never delete an
  application volume to make space.

## Steps

### Confirm usage and inodes

```bash
scripts/recon.sh <host>                 # Disk section already sorts fullest-first, usage + inodes
ssh svc-ops@<host> df -hP               # bytes
ssh svc-ops@<host> df -iP               # inodes — a full inode table reads as "disk full", space free
```

### Find the cause

```bash
# biggest dirs under the full mount (root may be needed for some paths → narrowest-host grant)
ssh svc-ops@<host> 'du -xh --max-depth=1 /var 2>/dev/null | sort -h | tail'
ssh svc-ops@<host> docker system df                 # images / containers / volumes / build cache
ssh svc-ops@<host> journalctl --disk-usage          # the systemd journal itself
ssh svc-ops@<host> 'du -sh /var/lib/docker/containers/*/*-json.log 2>/dev/null | sort -h | tail'
```

| Signal | Likely cause | Fix routes to |
|---|---|---|
| inodes at 100%, bytes free | a flood of tiny files (broken rotation, session/tmp files) | fix the producer; rotation config |
| docker overlay / build cache huge | dangling images + build cache | a pruning pass, then a CI/deploy hygiene fix |
| one container `*-json.log` huge | no log limit on that service | `logging` `max-size`/`max-file` in its compose |
| `journalctl --disk-usage` huge | unbounded journal | `SystemMaxUse` in journald config |
| one app volume growing | real data growth | expand the disk (tofu/Proxmox, grant) or a retention policy |

Emergency reclaim (careful, reversible cruft only): `docker image prune`, `journalctl --vacuum-size=200M`.
Never delete an app volume to make space — back it up first ([backup-missed](backup-missed.md)).

### Fix declaratively

- **Runaway container logs** → add `logging: {driver: json-file, options: {max-size: "10m", max-file: "3"}}`
  to `compose/<svc>/` → PR → Arcane reconciles.
- **Journal** → journald drop-in in the host's config module.
- **Genuinely out of room** → resize the disk via the declared infra (tofu/Proxmox) under a
  **narrowest-host, shortest-duration** grant, then reconcile inventory.

## Verify

Confirm the affected filesystem and inode table have safe headroom, the service can write normally, and
the declared rotation, logging, journald, retention, or disk-size change is active after reconciliation.

## Rollback

Revert the logging, journald, or infrastructure PR. If an emergency prune was required, stop after
reclaiming reversible cache/log cruft and restore from backup before any data removal; never undo a disk
resize by shrinking a live filesystem.

## Evidence

`bin/new journal incident "<host> disk full — <what ate it>"` — the mount, what `du` blamed, the config
PR or grant that resolved it. ([journal](../../journal/README.md).)
