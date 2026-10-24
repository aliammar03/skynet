# aiometadata

- **Purpose:** AIOMetadata, a Stremio metadata addon: catalogs, metadata and posters (TMDB, TVDB,
  Fanart, MDBList, RPDB), anime through `jikan`.
- **URL:** https://aiometadata.aliammar.net (caddy-apps → `aiometadata:3232` on `edge`). Public through
  the tunnel: Stremio clients call the addon from anywhere.
- **Auth mode:** oidc: sign-in through the apps' Authelia (client `aiometadata`). Groups map to
  permissions: `admins` → admin, `family` → createConfig. The addon's own URLs (the ones Stremio
  holds) carry their config and need no sign-in.
- **Containers:** `aiometadata`, and `aiometadata-redis` (its cache) on the stack's own internal
  `backend` network.
- **Data:** `/opt/appdata/aiometadata/` (copied from v1):
  - `data`: the database: configs and accounts (backup class: data);
  - `cold-store`: metadata kept beyond redis (backup class: cache);
  - `redis`: redis's append-only file (backup class: cache);
  - `poster-cache`: posters, refilled on demand, capped at 20 GB (backup class: cache; not copied).
- **Secrets:**
  - `secret.sops.env` (from v1): `ADMIN_KEY`, `IMAGE_PROXY_SIGNING_SECRET` (signs poster URLs: keep
    v1's, or posters in clients' cached catalogs break), `DATABASE_URI`, `REDIS_PASSWORD`,
    `TMDB_API_KEY`, `TVDB_API_KEY`, `FANART_API_KEY`, `FANART_API_PROJECT_KEY`, `MDBLIST_API_KEY`,
    `RPDB_API_KEY`, `GEMINI_API_KEY`, and v1's unused `OIDC_CLIENT_ID`/`OIDC_CLIENT_SECRET`. The
    six API keys reach the app only as `BUILT_IN_*` (compose interpolates them): under their own
    names aiometadata would publish them;
  - `oidc.sops.env` (agent-generated): `OIDC_CLIENT_SECRET` for the apps' Authelia. It's listed
    after `secret.sops.env`, so it wins; the client ID is in compose.
- **Upstream:** [AIOMetadata](https://github.com/cedya77/aiometadata) ·
  [SSO](https://github.com/cedya77/aiometadata/blob/main/docs/sso.md)

**Gotchas**
- A version tag (`3.7.0`), not the moving `latest` v1 used, so Renovate proposes each release.
- `REDIS_PASSWORD` reaches `REDIS_URL` and the redis container by interpolation (`.doco-cd.yml` →
  `env_files`), so a changed value needs a redeploy, not a restart. So do the API keys.
- `/api/config` answers anyone, sign-in or not, and returns `TMDB_API_KEY`, `TVDB_API_KEY`,
  `FANART_API_KEY`, `RPDB_API_KEY`, `MDBLIST_API_KEY` and `GEMINI_API_KEY` in full, to prefill the
  configure page. They stay blank; the `BUILT_IN_` copies are used, never sent
  (`hasBuiltIn…: true` there).
- A setting saved in its dashboard (table `addon_settings`) wins over compose's environment, unless
  the setting is env-only. So keys go in `secret.sops.env`, never the dashboard: saved there, the
  published ones are served again, whatever compose says. "Reset" in the dashboard deletes a saved
  value.
- It calls its issuer (`login.aliammar.net`) from inside: caddy-apps answers that name on `edge`
  (a network alias), because the host can't reach its own macvlan IPs.
- `TRUST_PROXY_HOPS=2`: caddy-apps, plus cloudflared for public requests. With 1 it would rate-limit
  every public visitor as 10.10.100.33.
