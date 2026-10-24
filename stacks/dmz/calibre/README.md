# calibre

- **Purpose:** the e-book library: Calibre's desktop app, streamed to the browser.
- **URL:** https://calibre.aliammar.net (caddy-apps → `calibre:8080` on `edge`). Public through the
  tunnel.
- **Auth mode:** forward: the apps' Authelia, group `admins`, a password (`one_factor`). Calibre's
  desktop has no login of its own, so whoever passes Authelia controls the whole library.
- **Data:** `/opt/appdata/calibre/config` → `/config`: the library, Calibre's settings and the
  desktop's home (owner 1000; backup class: data). Copied from v1.
- **Secrets:** none.
- **Upstream:** [linuxserver/calibre](https://docs.linuxserver.io/images/docker-calibre/)

**Gotchas**
- The image is v1's build, `v9.13.0-ls415` (v1 pinned `latest` at it). Calibre upgrades the library
  database on open, so a newer one comes as its own Renovate PR.
- The image's `EXPOSE` says 3000, but it sets `CUSTOM_PORT=8080` and serves there.
- Public and admin-only behind a password: once a passkey is registered on `login`, move its rule
  to `two_factor` (`stacks/dmz/authelia/configuration.yml`).
