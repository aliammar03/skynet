---
summary: "Take a bounded T1 host snapshot, interpret its signals, and route to the focused diagnosis runbook."
trigger: "Figure out why X is broken / what's going on with <host>"
tier: "T1 read-only"
executor: "scripts/recon.sh"
rollback: "none; recon does not mutate"
---

# Runbook — reconnaissance

**Tier:** T1 read-only. Diagnose imperatively; fix declaratively through the relevant source/PR.

## Preconditions

- Select the affected host from the generated host map. No grant is required to observe it.

## Steps

1. Capture the snapshot:
   ```bash
   scripts/recon.sh <host>
   scripts/recon.sh <host> > /tmp/recon-<host>.md
   scripts/recon.sh <host> --json
   ```
   `<host>` can be a mapped label or explicit `user@host`; no argument inspects the ops VM. Each probe is bounded by `RECON_TIMEOUT` (default six seconds), and sections requiring root say so instead of requesting a grant.
2. Read the returned host/kernel/uptime, pressure (including inodes), failed units, sockets, container state, warnings, and recent configuration/package changes. A failed unit, unhealthy container, full/inode-exhausted filesystem, or change immediately before failure is usually the best starting signal.
3. Follow the focused branch (the script prints likely matches):

   | Signal | Runbook |
   |---|---|
   | container unhealthy, exited, or restarting | [`diagnose/container-crashloop.md`](diagnose/container-crashloop.md) |
   | disk or inode exhaustion | [`diagnose/disk-full.md`](diagnose/disk-full.md) |
   | hostname resolution failure | [`diagnose/dns-failure.md`](diagnose/dns-failure.md) |
   | TLS/ACME problem | [`diagnose/cert-expired.md`](diagnose/cert-expired.md) |
   | missing backup or failed backup timer | [`diagnose/backup-missed.md`](diagnose/backup-missed.md) |
   | merged Compose change did not reconcile | [`diagnose/arcane-stuck.md`](diagnose/arcane-stuck.md) |

## Verify

- The snapshot identifies the host, relevant health/pressure signals, and a next diagnosis path.

## Rollback

- None. Recon is read-only and never replaces a declarative fix.

## Evidence

- Attach the snapshot to the incident/journal record. Reconcile any emergency imperative change into declared state in the same session.
