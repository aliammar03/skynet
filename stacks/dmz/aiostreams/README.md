# aiostreams

- **Purpose:** AIOStreams, a Stremio addon that gathers streams from many sources (debrid, usenet,
  other addons) into one.
- **URL:** https://aiostreams.aliammar.net (caddy-apps → `aiostreams:3000` on the `dmz` macvlan).
  Public through the tunnel: Stremio clients call the addon from anywhere.
- **Auth mode:** oidc: sign-in through the apps' Authelia (client `aiostreams`), beside its own local
  login (`AIOSTREAMS_AUTH`). Groups map to permissions: `admins` → admin, `family` → createConfig.
  The addon's own URLs (the ones Stremio holds) carry their config and need no sign-in.
- **Network:** only the `dmz` macvlan, at 10.10.100.65 (v1's address), so OPNsense rule 820
  (`ROLE_USENET_CLIENTS` → usenet 119/563) still names it. Not on `edge`: a public app with a foot in
  both networks would reach every app on `edge` and every neighbour on the macvlan.
- **Data:** `/opt/appdata/aiostreams/data` → `/app/data`: the database (users, configs; backup class:
  data). Copied from v1.
- **Secrets:**
  - `secret.sops.env` (from v1): `SECRET_KEY` (encrypts stored configs: keep v1's, or every saved
    config is lost), `DATABASE_URI`, `AIOSTREAMS_AUTH`, and v1's unused
    `AIOSTREAMS_OIDC_CLIENT_ID`/`_SECRET`;
  - `oidc.sops.env` (agent-generated): `AIOSTREAMS_OIDC_CLIENT_SECRET` for the apps' Authelia. It's
    listed after `secret.sops.env`, so it wins; the client ID is in compose.
- **Upstream:** [AIOStreams](https://github.com/Viren070/AIOStreams) ·
  [SSO](https://github.com/Viren070/AIOStreams/blob/main/packages/docs/content/docs/guides/sso.mdx)

**Gotchas**
- v1's build, `2026.08.12.1359-nightly` (v1 pinned `nightly` at it). Renovate proposes newer ones;
  nightlies move fast, so take them deliberately.
- It calls its issuer (`login.aliammar.net`) and aiometadata from inside, through Technitium: both
  are .35, caddy-apps' address on the same macvlan.
