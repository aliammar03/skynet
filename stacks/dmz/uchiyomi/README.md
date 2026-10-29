# uchiyomi

- **Purpose:** on trial (P8): finds manga and comics on their sources (MangaDex built in; Mihon's
  extensions through its engine), follows series and downloads their new chapters as CBZ to Unraid,
  and reads them: a webtoon-first reader, a PWA that also reads offline, OPDS and a Komga-compatible
  API for apps.
- **URL:** https://uchiyomi.aliammar.net (caddy-apps → `uchiyomi:3000` on `door-uchiyomi`). Inside and
  over Tailscale; not public.
- **Auth mode:** own, plus oidc: sign-in through the apps' Authelia (client `uchiyomi`, policy
  `admins`). The first sign-in makes the account (`OIDC_ALLOW_SIGNUP`), and group `admins` makes it
  an admin at every sign-in (`OIDC_ADMIN_GROUP`). The agent's own admin (`skynet`) made the first-run
  setup (D16; its password is `secrets/ops.uchiyomi.yaml`).
- **Services:**
  - `uchiyomi`: the app, with its own Postgres 16 inside (on a socket, no password);
  - `uchiyomi-suwayomi`: the extension engine (Suwayomi, headless), which runs Mihon's extensions for
    Uchiyomi. Uchiyomi does the downloading; the engine never writes into the library;
  - `uchiyomi-flaresolverr`: the Cloudflare solver (a headless Chrome) for sources behind Cloudflare,
    for the app and the engine.
- **Network:** the app on `door-uchiyomi` (internal, shared with caddy-apps alone, from
  `hosts/docker-dmz`; it reaches its issuer there as `login.aliammar.net`) and `backend`, the stack's
  own network with the engine and the solver, and its way out. Only the app is routed.
- **Library:** on Unraid's `Storage` (`hosts/docker-dmz`: `/mnt/storage`): Ali's `Books/Manga` and
  `Books/Comics`, read-only at `/library/Manga` and `/library/Comics`, and its downloads in
  `Books/Downloads` → `/library-dl`, as `<source>/<series>/Chapter N.cbz`. It runs as `99:100`
  (`PUID`/`PGID`), Unraid's `nobody:users`. Its libraries are lists of these folders: Manga
  (`Manga`, and the manga sources' folders), Comics (`Comics`, the comic sources' folders, AniList off).
- **Data:**
  - `/opt/appdata/uchiyomi/data` → `/data`: its Postgres (backup class: data);
  - `/opt/appdata/uchiyomi/config` → `/config`: session and push keys, sites added by address (data);
  - `/opt/appdata/uchiyomi/backups` → `/backups`: its nightly database dumps, 14 kept (data);
  - `/opt/appdata/uchiyomi/engine` → the engine's extensions, database and settings (owner 1000,
    from `hosts/docker-dmz`; data), its `cache/` excluded (`stacks/dmz/backup/excludes.txt`);
  - `/var/cache/uchiyomi` → `/cache`: page images, capped at 5 GiB (`CACHE_MAX_BYTES`), on the host's
    ext4: outside `/opt/appdata`, its snapshots and the backup.
- **Secrets:** `oidc.sops.env`: `OIDC_CLIENT_SECRET` (agent-generated; its digest is in
  `stacks/dmz/authelia/oidc-clients.yml`). The engine has no password: only this stack's network
  reaches it.
- **Upstream:** [Uchiyomi](https://github.com/AngeloSha/uchiyomi) ([API](https://github.com/AngeloSha/uchiyomi/blob/main/docs/api.md),
  also at `/api/docs`) · [Suwayomi-Server](https://github.com/Suwayomi/Suwayomi-Server) ·
  [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr)

**Gotchas**
- Until its first-run setup, whoever opens it first makes the admin. A fresh `/opt/appdata/uchiyomi`
  is set up again by the agent (`POST /api/setup`).
- The engine's tag moves only with an Uchiyomi release that names it: it upgrades its database one
  way, so back up `engine/` first (upstream's `docs/extensions.md`).
- The engine's Chromium logs D-Bus errors at start; they're harmless.
- The library folders are `create_host_path: false`: with Unraid down, the app doesn't start
  (doco-cd retries it) rather than download onto docker-dmz's own disk.
