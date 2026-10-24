# sillytavern

- **Purpose:** SillyTavern, the AI chat front end (characters, chats, image generation through
  ComfyUI on the workstation).
- **URL:** https://sillytavern.aliammar.net (caddy-apps → `sillytavern:8000` on `edge`). Inside only.
- **Auth mode:** forward: the apps' Authelia, group `admins`, a password (`one_factor`). Behind it,
  SillyTavern's own IP whitelist (`SILLYTAVERN_WHITELIST`: the lab and the tailnet), which it checks
  against `X-Forwarded-For` (`enableForwardedWhitelist` in `config.yaml`).
- **Network:** also on the `dmz` macvlan at 10.10.100.69 (v1's address, `gw_priority: 1`), so OPNsense
  rule 340 (`ROLE_DMZ_AI_CLIENTS` → the workstation's ComfyUI :8188) still names it.
- **Data:** `/opt/appdata/sillytavern/` (owner 1000; backup class: data): `config` (its
  `config.yaml`), `data` (characters, chats, settings), `plugins`, `extensions` (third-party UI
  extensions). Copied from v1.
- **Secrets:** none of its own; API keys live in its `data` (SillyTavern's secrets.json).
- **Upstream:** [SillyTavern](https://docs.sillytavern.app/)

**Gotchas**
- v1 pinned the moving `release` tag at a digest no version tag carries; it stays pinned there until a
  Renovate PR moves it.
- The whitelist must include the tailnet (100.64.0.0/10), or it refuses phones over Tailscale even
  after Authelia.
