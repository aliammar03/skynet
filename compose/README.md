# compose — one dir per service, Arcane git-syncs each

```
compose/<service>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; Arcane makes this read-only in its UI
├── .env.git       # NON-secret config, committed plaintext — Arcane's git layer
└── .env.sops      # secrets ONLY, sops+age (keys visible in diffs, values encrypted)
```

**The canonical "skynet way" for every service** (the standard this repo enforces):
digest-pinned images · `env_file: .env` · non-secret config in committed `.env.git` ·
secrets only in `.env.sops` · deployed via Arcane GitOps Sync from this repo. No inline compose
config, no file-based `.txt` docker secrets. Deploy with `scripts/gitops-deploy.sh <svc>` — see
`runbooks/deploy-service.md` for how the effective `.env` is materialised (Arcane GitOps does not
merge `.env.git`/`project.env`).

### Volume standard — the decision (apply to EVERY mount a service needs)

| the data is… | → type | host name | label |
|---|---|---|---|
| a **standalone DB-engine** container's storage — mongo, postgres, standalone redis, **meilisearch**, typesense, elasticsearch… | **named volume** | `<role>` (docker-managed; compose prefixes `<svc>_`) | **required** on the volume: `com.aliammar.service: <svc>` + `com.aliammar.backup: critical\|rebuildable` |
| **everything else** — app data, configs, uploads, media, an app's **embedded SQLite** | **bind mount** | `/opt/docker/appdata/<svc>/<role>` | none (located by path; in the restic appdata sweep) |
| a **repo-tracked** config/code file (init scripts, patches) | relative mount | `./…:…:ro` (GitOps-synced) | none |

Rules that make it unambiguous:
- `<svc>` = the compose dir name (lowercase). `<role>` = a short purpose noun: `data`, `config`,
  `index`, `db`, `plugins`… **Every bind mount gets a `<role>` subdir even if the service has only
  one** (so `…/calibre/config`, never `…/calibre`). Don't repeat `<svc>` in `<role>`
  (`…/marinara/data`, not `…/marinara/marinara-data`).
- **`critical`** = primary source of truth, not reconstructable (user data, a primary DB).
  **`rebuildable`** = cache / derived / re-indexable (search indexes, redis-as-cache, poster caches).
- `backup-restic.sh` backs up `/opt/docker/appdata` (all bind mounts) **plus** named volumes
  labelled `com.aliammar.backup=critical`. Rebuildable named volumes are never backed up; put a
  rebuildable *bind-mount* cache under a name matched by the script's `--exclude` list.
- Switching a named volume ↔ bind mount: remove the orphan (`docker volume rm <svc>_<role>`, or
  `rm -rf` the stale appdata dir) so restic doesn't grab dead data.

## The env-layering contract (Arcane, resolved in plan §4)

Arcane merges two layers into the effective `.env`:

- **`.env.git`** — repo-sourced, non-secret defaults (optional, committed plaintext).
- **`project.env`** — your UI edits, the **secret-bearing** layer, not reproducible from the repo.
  Your overrides always win; Arcane rewrites in place preserving order/comments. No clobbering by design.

Therefore:

1. `project.env` is what `scripts/envsync.sh` encrypts → `.env.sops` (nightly, on change).
2. **Every service must declare `env_file: .env`** in its compose so the merged values reach it.
3. Non-secret defaults *may* be a committed plaintext `.env` (ingested as `.env.git`); **secrets never**.
4. Auto-sync **only redeploys already-running projects** — a stopped project updates on next manual start.

Restore: `sops -d compose/<svc>/.env.sops > project.env` into the project dir; Arcane re-merges.
