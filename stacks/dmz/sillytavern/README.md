# sillytavern

- **Purpose:** SillyTavern, the AI chat front end (characters, chats, image generation through
  ComfyUI on the workstation).
- **URL:** https://sillytavern.aliammar.net (caddy-apps → `sillytavern:8000` on the `dmz` macvlan).
  Inside only.
- **Auth mode:** forward: the apps' Authelia, group `admins`, a password (`one_factor`). Behind it,
  SillyTavern's own whitelist admits one connecting address, caddy-apps' (`SILLYTAVERN_WHITELIST`,
  plus loopback for its healthcheck), so its macvlan neighbours get 403. Compose turns off
  `enableForwardedWhitelist` (on in `config.yaml`): with it, `X-Forwarded-For` would have to be in
  the list too, so it would have to list every client.
- **Network:** only the `dmz` macvlan, at 10.10.100.69 (v1's address): OPNsense rule 340
  (`ROLE_DMZ_AI_CLIENTS` → the workstation's ComfyUI :8188) still names it, and no app on `edge`
  reaches it.
- **Data:** `/opt/appdata/sillytavern/` (owner 1000; backup class: data): `config` (its
  `config.yaml`), `data` (characters, chats, settings), `plugins`, `extensions` (third-party UI
  extensions). Copied from v1.
- **Secrets:** none of its own; API keys live in its `data` (SillyTavern's secrets.json).
- **Upstream:** [SillyTavern](https://docs.sillytavern.app/)

**Gotchas**
- v1 pinned the moving `release` tag at a digest no version tag carries; it stays pinned there until a
  Renovate PR moves it.
- `SILLYTAVERN_<KEY>` overrides `config.yaml`'s `<key>` (e.g. `SILLYTAVERN_WHITELIST`). The gate's
  settings are in compose for that reason, not in `config.yaml`, which is app data.
