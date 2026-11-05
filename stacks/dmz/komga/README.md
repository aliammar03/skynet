# komga

- **Purpose:** the comics and manga library (P8): a series per folder at any depth, a web reader
  (right to left, double pages, webtoon scroll), and feeds for iPad apps: OPDS
  (`/opds/v1.2/catalog`, for Panels) and its own API (Komic).
  - `komf` (Komf 2.1, `komf.yml`; Ali, 2026-11-05): the Manga library's metadata and covers,
    through Komga's API only: no file is touched (they're Uchiyomi's). AniList, then MangaUpdates,
    then MangaDex, each filling what the one before lacks: summary, status, genres, tags, authors,
    score, links, alternative titles, and the series' cover art, which Uchiyomi's files lack. Series
    titles stay as the folders name them; a chapter gets the series' authors and links, not a title
    or the series' summary. A series added is matched when Komga reports it.
  - `komga-wiki` (`wiki/wiki.py`; Ali, 2026-11-05): a manga chapter's own title and summary, from the
    series' fan wiki, which the comics agent links (Komga's link labelled "Wiki", to its page for
    chapter 1; comics-tools' `manga/wiki`). Hourly, it reads each chapter's page through the
    wiki's MediaWiki API (a request a second), takes the infobox's title and the short summary as
    plain text, and writes both into Komga, locked: nothing overwrites them, and a chapter with
    both is never read again. A chapter the wiki hasn't written yet is read again a week later. A
    Wiki link a later Komf match drops is put back. It also clears the series' description from
    every manga chapter, linked or not: Uchiyomi writes it into each chapter's ComicInfo, and Komga
    reads it from there. A chapter shows its own summary or none.
  - Comics need neither: each issue's ComicInfo (Metron, through CLU) is right, and every series'
    cover is its issue #1's, `folder.png` from CLU (its folder art set to Single Image, Ali
    2026-11-05; a pinned issue in CLU replaces it).
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
  (`database.sqlite`; data). `/opt/appdata/komga/wiki` → komga-wiki's `/data`: each series' wiki and
  when a chapter was last read (`state.json`; data).
- **Secrets:**
  - `oidc.sops.env`: `SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHELIA_CLIENT_SECRET`
    (agent-generated; its digest is in `stacks/dmz/authelia/oidc-clients.yml`).
  - `komf.sops.env`, Komf's and komga-wiki's: `KOMF_KOMGA_PASSWORD` (their Komga account,
    `komf@aliammar.net`, an administrator: only an admin edits metadata), Ali's. It also holds Ali's
    `KOMF_METADATA_PROVIDERS_COMIC_VINE_API_KEY`, which Komf no longer uses.
- **Setup (Komf, once):** Ali makes the account (Komga → Server → Users → add `komf@aliammar.net`,
  Administrator) and puts its password into `komf.sops.env`
  (`nix shell nixpkgs#sops -c sops stacks/dmz/komga/komf.sops.env`). After the deploy the agent
  matches what's already there and spot-checks the result:
  `docker exec komf curl -fsS -X POST http://127.0.0.1:8085/komga/match/library/0S2GKXTMMD47G`
  (the Manga library).
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
- Komf's `reset` also gives the chapters Komga's defaults: the file's name as title, and their
  position as number (1, 2, 3…, wrong for a series that starts at chapter 1126). A metadata refresh
  of the series in Komga reads the files' numbers back (`POST /api/v1/series/<id>/metadata/refresh`);
  until then komga-wiki leaves those chapters alone.
- Komf matches a series by its name; a match is checked against the series' author after the first
  pass.
- Komf's covers are uploaded thumbnails, selected in Komga; Komga's own (the first book's first
  page) stays, a click away. A comics series' cover is a sidecar (`folder.png`), which Komga
  selects at its next scan.
- Komf's Comic Vine provider can't read Comic Vine's answers since Comic Vine changed a field from
  text to a number (Komf #350, open since 2026-10-23); it would only offer smaller copies of the
  covers CLU already gives.
- A wiki is linked by its page for chapter 1, and that page's name gives every other's: `Chapter_1` →
  `Chapter_1126`, `Chapter_001` → `Chapter_007`. A wiki that names its pages otherwise doesn't fill.
- A chapter's title or summary edited and locked by hand in Komga stays: komga-wiki writes only what
  isn't locked.
