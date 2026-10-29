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
  - `uchiyomi-suwayomi`: the extension engine (Suwayomi v2.4), which runs Mihon's extensions for
    Uchiyomi. Uchiyomi does its own downloading; the engine never writes into its library. For the
    trial it is also Ali's Suwayomi, at https://suwayomi.aliammar.net (caddy-apps →
    `uchiyomi-suwayomi:4567` on `door-suwayomi`; auth forward, the apps' Authelia, `admins`): its own
    web UI, library and downloads, sharing the extensions with Uchiyomi. Its downloads go to
    `Books/Manga/suwayomi` as `mangas/<source>/<series>/`, each comic source's folder mounted over
    from `Books/Comics/suwayomi/<source>`; it downloads followed series' new chapters by itself;
  - `uchiyomi-flaresolverr`: the Cloudflare solver (a headless Chrome) for sources behind Cloudflare,
    for the app and the engine.
- **Network:** the app on `door-uchiyomi` (internal, shared with caddy-apps alone, from
  `hosts/docker-dmz`; it reaches its issuer there as `login.aliammar.net`) and `backend`, the stack's
  own network with the engine and the solver, and its way out. The engine also sits on
  `door-suwayomi`, with caddy-apps alone, for its web UI.
- **Library:** on Unraid's `Storage` (`hosts/docker-dmz`: `/mnt/storage`), sorted by type:
  - read-only: Ali's `Books/Manga/library` → `/library/Manga`, `Books/Comics/library` →
    `/library/Comics`, Kapowarr's `Books/Comics/kapowarr` → `/library/Kapowarr`, Mylar3's
    `Books/Comics/mylar3` → `/library/Mylar3`, and CLU's `Books/Comics/clu` → `/library/CLU`;
  - its downloads, `/library-dl`, as `<source>/<series>/Chapter N.cbz`: `Books/Manga/uchiyomi`, with
    each comic source's folder mounted over it from `Books/Comics/uchiyomi/<source>` (one compose
    line per comic extension: BatCave, ComicHubFree, Read Comics Online, XOXO Comics).

  It runs as `99:100` (`PUID`/`PGID`), Unraid's `nobody:users`. Its libraries are lists of folders:
  Comics (`Comics`, `Kapowarr`, `Mylar3`, `CLU` and the comic sources' folders; AniList off) and
  Manga (the default: everything else).
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
- A new comic extension: its folder in `Books/Comics/uchiyomi/` and its line in compose (PR), or its
  downloads land in Manga. A symlink won't do: Uchiyomi refuses a download path that leaves
  `/library-dl`.
- BatCave passes its site's check (DLE Guard) only through Open site: done once 2026-10-29, and
  Uchiyomi revisits its home page whenever it fails. Admin → Sources → BatCave → Open site → Done
  if it stays red.
