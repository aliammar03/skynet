# komga

- **Purpose:** the comics and manga library (P8): a series per folder at any depth, a web reader
  (right to left, double pages, webtoon scroll), and feeds for iPad apps: OPDS
  (`/opds/v1.2/catalog`, for Panels) and its own API (Komic).
- **URL:** https://komga.aliammar.net (caddy-apps → `komga:25600` on `door-komga`). Inside and over
  Tailscale; not public.
- **Auth mode:** own, plus oidc: sign-in through the apps' Authelia (client `komga`, policy `admins`).
  The first sign-in makes the account, matched by email, as a plain user; the agent makes Ali's an
  admin. The agent's own admin (`skynet@aliammar.net`) claimed the server first (D16; its password
  is `secrets/ops.komga.yaml`). iPad apps use an API key (`X-API-Key`), one per app, made in the
  account's settings.
- **Network:** only `door-komga`, an internal bridge it shares with caddy-apps alone (from
  `hosts/docker-dmz`): nothing else reaches it, and it has no way out. It reaches its issuer as
  `login.aliammar.net`, caddy-apps' alias there; it doesn't start until that answers.
- **Libraries:** on Unraid's `Storage`, read-only (`hosts/docker-dmz`: `/mnt/storage`):
  `Books/Manga` → `/books/Manga` and `Books/Comics` → `/books/Comics`, a library each (a Komga
  library is one folder, at any depth). Each holds Ali's own files (`library/`) and the
  downloaders' (`uchiyomi/`, `suwayomi/`, `kapowarr/`, `mylar3/`, `clu/`).
- **Data:** `/opt/appdata/komga/config` → `/config`: its database, thumbnails, search index and
  sessions (backup class: data), and `logs/` (cache: `stacks/dmz/backup/excludes.txt`).
- **Secrets:** `oidc.sops.env`: `SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHELIA_CLIENT_SECRET`
  (agent-generated; its digest is in `stacks/dmz/authelia/oidc-clients.yml`).
- **Upstream:** [Komga](https://komga.org/docs/introduction) ·
  [Authelia's Komga guide](https://www.authelia.com/integration/openid-connect/clients/komga/)

**Gotchas**
- An unclaimed Komga makes whoever claims it (`POST /api/v1/claim`) its admin. A fresh
  `/opt/appdata/komga` is unclaimed until the agent claims it again.
- The OIDC settings are Spring properties, as environment variables: `KOMGA_OAUTH2_ACCOUNT_CREATION`
  and `SPRING_SECURITY_OAUTH2_CLIENT_…_AUTHELIA_…` in compose.
- Its heap is pinned (`-Xmx512m`): a JVM would size it from the container's limit.
