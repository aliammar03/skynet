# jikan

- **Purpose:** Jikan, a self-hosted MyAnimeList API. aiometadata reads anime metadata from it
  (`JIKAN_API_BASE=http://jikan:8080/v4`).
- **URL:** none. aiometadata reaches `jikan:8080` on `edge`; no route, no DNS name, no Gatus row
  (aiometadata's row covers it).
- **Auth mode:** none (not routed).
- **Containers:** `jikan` (the API; on `edge` for aiometadata and for MyAnimeList), and on the
  stack's own internal `backend` network `jikan-mongo` (the anime database), `jikan-redis` (its
  cache), `jikan-typesense` (its search index).
- **Data:** `/opt/appdata/jikan/` (copied from v1's `aiometadata_jikan_*` volumes): `mongo` (owner
  999; backup class: data), `redis` and `typesense` (backup class: cache; both rebuild).
- **Secrets** (`secret.sops.env`, v1's `JIKAN_*` from aiometadata's file): `JIKAN_DB_USERNAME`,
  `JIKAN_DB_PASSWORD`, `JIKAN_DB_ADMIN_USERNAME`, `JIKAN_DB_ADMIN_PASSWORD`, `JIKAN_REDIS_PASSWORD`,
  `JIKAN_TYPESENSE_API_KEY`. Compose interpolates them (`.doco-cd.yml` → `env_files`), because each
  container wants them under its own names.
- **Files:** `RepositoryQuery.php` (v1's override: filters and searches go through Mongo, not
  Typesense); `mongo-init.js` (the app user and indexes, run on an empty data directory only).
- **Upstream:** [jikan-rest](https://github.com/jikan-me/jikan-rest)

**Gotchas**
- Mongo (6.0.4) and Typesense (0.24.1) stay at v1's versions: they hold on-disk formats. Mongo
  upgrades one major version at a time.
- A changed `JIKAN_*` value reaches the containers only through a redeploy (interpolation), not a
  restart.
