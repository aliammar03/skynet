# marinara

- **Purpose:** Marinara Engine, AI roleplay (chats, characters, image generation through ComfyUI on
  the workstation).
- **URL:** https://marinara.aliammar.net (caddy-apps → `marinara:7860` on `edge`). Inside only.
- **Auth mode:** own, but open from inside, as in v1: it lets private networks
  (`ALLOW_UNAUTHENTICATED_PRIVATE_NETWORK`, `TRUSTED_PRIVATE_NETWORKS`) and Docker hosts
  (`BYPASS_AUTH_DOCKER`) in without a login, and caddy-apps is both. Its basic auth
  (`BASIC_AUTH_USER`/`PASS`) applies to anything else. So any app client that reaches caddy-apps
  (rule 200: VLANs 10, 20, 30, 40) can open it.
- **Network:** also on the `dmz` macvlan at 10.10.100.85 (v1's address, `gw_priority: 1`), so OPNsense
  rule 340 (`ROLE_DMZ_AI_CLIENTS` → the workstation's ComfyUI :8188) still names it.
- **Data:** `/opt/appdata/marinara/data` → `/app/data` (owner 1000; backup class: data). Copied from
  v1.
- **Secrets** (`secret.sops.env`, from v1): `ENCRYPTION_KEY` (encrypts the API keys it stores; lose it
  and they're unreadable), `ADMIN_SECRET`, `SSL_CERT`, `SSL_KEY`, `BASIC_AUTH_USER`,
  `BASIC_AUTH_PASS`, `GIPHY_API_KEY`.
- **Upstream:** [Marinara Engine](https://github.com/Pasta-Devs/Marinara-Engine)

**Gotchas**
- v1's build, `2.4.1` (v1 pinned `latest` at it). It may check for updates but never applies them
  (`UPDATES_APPLY_ENABLED=false`); Renovate proposes newer images.
- To put it behind the apps' Authelia instead, add `import authelia` to its site and a rule for
  `marinara.aliammar.net`.
