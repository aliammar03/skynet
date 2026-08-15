# Runbook — restore a service (conversational, deterministic)

**Tier:** T2 + (if VM restore) T2 PBS token. **Goal:** any agent can execute this verbatim.

## "Restore <svc> to <when>" (container app data)

The docker-dmz restic repo is `rclone:gdrive:Skynet/Backups/restic/docker-dmz`
(env: `/opt/skynet-ops/secrets/restic-docker-dmz.env` on the host; needs a root grant —
`gr vm-docker-dmz`). It backs up `/opt/docker/appdata` **plus** named volumes labelled
`skynet.backup=protect` (resolved to their `/var/lib/docker/volumes/<vol>/_data` mountpoints).

1. **Pause Arcane sync** for the project so auto-sync can't fight the restore:
   `PUT /api/environments/0/gitops-syncs/<id> {"autoSync":false}`.
2. **Stop the stack**: `POST /api/environments/0/projects/<id>/down` (or `docker context`).
3. **Find + restore the snapshot** (as root on the host, env sourced):
   ```bash
   set -a; . /opt/skynet-ops/secrets/restic-docker-dmz.env; set +a
   restic snapshots                       # pick the dated <id>
   restic restore <id> --target / \
     --include /opt/docker/appdata/<svc> \
     --include /var/lib/docker/volumes/<svc>_<vol>/_data   # scope to this svc's paths
   ```
   Scoping with `--include` avoids clobbering other services' appdata. Restoring into wiped
   paths necessarily pulls the data blobs from Google Drive (clear `/root/.cache/restic`
   first if you want to *prove* an off-site fetch).
4. **Env for that point in time:** `git checkout <commit> -- compose/<svc>/.env.sops`, then
   redeploy with `scripts/gitops-deploy.sh <svc>` from skynet-ops — it materialises the
   effective `.env` (= `.env.git` + `sops -d .env.sops`, decrypted where the age key lives),
   redeploys, and health-checks. (Plain "restore to now" can skip the `git checkout`.)
5. **Resume Arcane sync** (`{"autoSync":true}`), **health check**, **report**.

> DB-backed services: verify DB consistency after restore (below). If a hot filesystem copy
> proves inconsistent under real load, add a `mongodump`/`pg_dump` pre-hook to
> `scripts/backup-restic.sh` that writes into `/opt/docker/appdata/<svc>/` before the sweep,
> then restore the dump per the service note.

## "Roll VM <id> back to <when>" (guest)

1. T2 PBS token → list snapshots → **PBS restore** into `ops-managed`.
2. Boot → verify. (Never restore an excluded guest without an explicit T3 grant.)

## "What can we restore right now?"

`restic snapshots` (per host) + PBS index + `git tag` / commit history. Report the menu.

## Per-service DB notes

_(append as services are onboarded: service → dump path → restore command)_

### aiometadata (mongo + SQLite) — **witnessed restore, 2026-08-16**

- **State backed up:** `/opt/docker/appdata/aiometadata/data` (holds `db.sqlite` in WAL mode,
  the addon's own DB; `poster-cache/` + `cold-store/` are excluded as rebuildable) and the
  named volume `aiometadata_jikan_mongo_data` (jikan's mongo, labelled `skynet.backup=protect`).
- **Consistency:** raw-volume restore of the hot copies was **verified consistent** — SQLite
  `PRAGMA integrity_check` = ok, and mongo (WiredTiger) recovered its journal on start with the
  data fingerprint (per-collection doc counts) byte-identical to pre-wipe. No pre-hook needed at
  current data volume; add a `mongodump` pre-hook if mongo later carries heavy write load.
- **A4 witness (proof the whole L3 path works):** snapshot `f157b5ec` restored from Google
  Drive after wiping `data/` + the mongo volume and clearing the restic cache; redeployed via
  `scripts/gitops-deploy.sh aiometadata`; all 6 containers returned `healthy`; mongo + SQLite
  verified as above.
