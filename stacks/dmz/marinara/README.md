# marinara

- **Purpose:** Marinara Engine, AI roleplay (chats, characters, image generation through ComfyUI on
  the workstation).
- **URL:** https://marinara.aliammar.net (caddy-apps → `marinara:7860` on the `dmz` macvlan). Inside
  only.
- **Auth mode:** forward: the apps' Authelia, group `admins`, a password (`one_factor`), and nothing
  else. Marinara's own basic auth is off (`BASIC_AUTH_USER`/`PASS` emptied in compose, which
  overrides v1's values in the secret file). With no login set, it admits one address, caddy-apps'
  (`IP_ALLOWLIST=10.10.100.35`); its macvlan neighbours get 403. Its Docker and Tailscale bypasses
  are off (`BYPASS_AUTH_DOCKER`, `BYPASS_AUTH_TAILSCALE`): each lets a whole range skip the
  allowlist. `ALLOW_UNAUTHENTICATED_*` are off too.
- **Network:** only the `dmz` macvlan, at 10.10.100.85 (v1's address): OPNsense rule 340
  (`ROLE_DMZ_AI_CLIENTS` → the workstation's ComfyUI :8188) still names it, and no app on `edge`
  reaches it.
- **Data:** `/opt/appdata/marinara/data` → `/app/data` (owner 1000; backup class: data). Copied from
  v1.
- **Secrets** (`secret.sops.env`, from v1): `ENCRYPTION_KEY` (encrypts the API keys it stores; lose it
  and they're unreadable), `ADMIN_SECRET`, `SSL_CERT`, `SSL_KEY`, `BASIC_AUTH_USER`,
  `BASIC_AUTH_PASS`, `GIPHY_API_KEY`.
- **Upstream:** [Marinara Engine](https://github.com/Pasta-Devs/Marinara-Engine)

**Gotchas**
- v1's build, `2.4.1` (v1 pinned `latest` at it). It may check for updates but never applies them
  (`UPDATES_APPLY_ENABLED=false`); Renovate proposes newer images.
- In this version, Docker trust never overrides a configured password: with `BASIC_AUTH_*` set,
  caddy-apps' requests get the basic-auth prompt (v1 prompted too). It does override the allowlist:
  with `BYPASS_AUTH_DOCKER=true`, every container in 172.16.0.0/12 gets in.
- It reads the client's address from the connection, not `X-Forwarded-For`, so the allowlist names
  the door, not the visitors.
