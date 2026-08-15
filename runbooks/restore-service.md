# Runbook — restore a service (conversational, deterministic)

**Tier:** T2 + (if VM restore) T2 PBS token. **Goal:** any agent can execute this verbatim.

## "Restore <svc> to <when>" (container app data)

1. **Pause Arcane sync** for the project (so it doesn't fight the restore).
2. **Stop the stack** (`docker context` / Arcane API).
3. **restic restore** the dated snapshot of `/opt/docker/appdata` for that host
   (`restic snapshots` to find it; `restic restore <id> --target /`).
4. **Env for that point in time:** `git checkout <commit> -- compose/<svc>/.env.sops`, then
   `sops -d compose/<svc>/.env.sops > project.env` in the project dir. Arcane re-merges with `.env.git`.
5. **Resume Arcane sync**, **health check**, **report**.

> DB-backed services: the nightly pre-hook dumped the DB into appdata. Restore the dump,
> then load it per the service's note below before starting the app.

## "Roll VM <id> back to <when>" (guest)

1. T2 PBS token → list snapshots → **PBS restore** into `ops-managed`.
2. Boot → verify. (Never restore an excluded guest without an explicit T3 grant.)

## "What can we restore right now?"

`restic snapshots` (per host) + PBS index + `git tag` / commit history. Report the menu.

## Per-service DB notes

_(append as services are onboarded: service → dump path → restore command)_
