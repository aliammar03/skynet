# komga

- **Purpose:** the comics and manga library (P8): a series per folder at any depth, a web reader
  (right to left, double pages, webtoon scroll), and feeds for iPad apps: OPDS
  (`/opds/v1.2/catalog`, for Panels) and its own API (Komic).
  - `komf` (Komf 2.1, `komf.yml`; Ali, 2026-11-05): metadata and covers, through Komga's API only:
    no file is touched (they're CLU's and Uchiyomi's). **Manga:** AniList, then MangaUpdates, then
    MangaDex, each filling what the one before lacks: summary, status, genres, tags, authors,
    score, links, alternative titles, and the series' cover art (Uchiyomi's chapters carry only a
    title and a number, and no cover). Series titles stay as the folders name them. **Comics:**
    Comic Vine, the series' cover only: each issue's own metadata (Metron, through CLU) and cover
    (its first page) are already right. A series added to either library is matched when Komga
    reports it.
- **URL:** https://komga.aliammar.net (caddy-apps → `komga:25600` on `door-komga`). Inside and over
  Tailscale; not public.
- **Auth mode:** own, plus oidc: sign-in through the apps' Authelia (client `komga`, policy `admins`).
  The first sign-in makes the account, matched by email, as a plain user; the agent makes Ali's an
  admin. The agent's own admin (`skynet@aliammar.net`) claimed the server first (D16; its password
  is `secrets/ops.komga.yaml`). iPad apps use an API key (`X-API-Key`), one per app, made in the
  account's settings.
- **Network:** `door-komga`, an internal bridge it shares with caddy-apps alone (from
  `hosts/docker-dmz`), and the stack's internal `backend`, which it shares with Komf alone: nothing
  else reaches it, and it has no way out. It reaches its issuer as `login.aliammar.net`, caddy-apps'
  alias there; it doesn't start until that answers. Komf: `backend` (Komga, by name) and the stack's
  `egress` (the providers). Its API has no login, so no other container shares a network with it.
- **Libraries:** on Unraid's `Storage`, read-only (`hosts/docker-dmz`: `/mnt/storage`):
  `Books/Manga` → `/books/Manga` and `Books/Comics` → `/books/Comics`, a library each (a Komga
  library is one folder, at any depth). Each holds Ali's own files (`library/`) and the
  downloaders' (`uchiyomi/`, `suwayomi/`, `clu/`). Both scan hourly and empty their trash after a
  scan (the agent sets it through the API, D16: `PATCH /api/v1/libraries/<id>`
  `{"scanInterval": "HOURLY", "emptyTrashAfterScan": true}`), so CLU's new issues show within the
  hour and a file renamed or removed leaves no entry behind. A library folder it can't read stops
  the scan and marks the library unavailable, so an unreachable share doesn't empty it.
- **Data:** `/opt/appdata/komga/config` → `/config`: its database, thumbnails (Komf's covers among
  them), search index and sessions (backup class: data), and `logs/` (cache:
  `stacks/dmz/backup/excludes.txt`). `/opt/appdata/komga/komf` → Komf's `/config`: its matches
  (`database.sqlite`; data).
- **Secrets:**
  - `oidc.sops.env`: `SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHELIA_CLIENT_SECRET`
    (agent-generated; its digest is in `stacks/dmz/authelia/oidc-clients.yml`).
  - `komf.sops.env`, Komf's: `KOMF_KOMGA_PASSWORD` (its Komga account, `komf@aliammar.net`, an
    administrator: only an admin edits metadata) and `KOMF_METADATA_PROVIDERS_COMIC_VINE_API_KEY`
    (Comic Vine's API page, on Ali's account). Both Ali's.
- **Setup (Komf, once):** Ali makes the account (Komga → Server → Users → add `komf@aliammar.net`,
  Administrator) and Comic Vine's key, and puts both into `komf.sops.env`
  (`nix shell nixpkgs#sops -c sops stacks/dmz/komga/komf.sops.env`). After the deploy the agent
  matches what's already there, a library at a time, and spot-checks the result:
  `docker exec komf curl -fsS -X POST http://127.0.0.1:8085/komga/match/library/<id>` (Manga
  `0S2GKXTMMD47G`, Comics `0S2GKXV8CD7Q4`).
- **Upstream:** [Komga](https://komga.org/docs/introduction) ·
  [Authelia's Komga guide](https://www.authelia.com/integration/openid-connect/clients/komga/) ·
  [Komf](https://github.com/Snd-R/komf)

**Gotchas**
- An unclaimed Komga makes whoever claims it (`POST /api/v1/claim`) its admin. A fresh
  `/opt/appdata/komga` is unclaimed until the agent claims it again.
- The OIDC settings are Spring properties, as environment variables: `KOMGA_OAUTH2_ACCOUNT_CREATION`
  and `SPRING_SECURITY_OAUTH2_CLIENT_…_AUTHELIA_…` in compose.
- Its heap is pinned (`-Xmx512m`): a JVM would size it from the container's limit.
- Komf's API is under `/komga/…` (`providers`, `search`, `identify`, `match/library/<id>[/series/<id>]`,
  `reset/library/<id>[/series/<id>]`); every other path is its web page, which answers 200 to
  anything. A wrong match is fixed with `identify` (the series and the provider's id), or undone
  with `reset`.
- Komf matches a series by its name. Comic Vine has many volumes of one name (relaunches): a comics
  series' cover is checked against the series after the first pass.
- Komf's covers are uploaded thumbnails, selected in Komga; Komga's own (the first book's first
  page) stays, a click away.
