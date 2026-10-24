# authelia (apps)

- **Purpose:** the apps' login portal and forward-auth for caddy-apps, separate from admin Authelia
  (`stacks/admin/authelia`): its own users, sessions and secrets. It's reachable from the internet
  through the tunnel, so it lives in the DMZ with the apps it guards (D4).
- **URL:** https://login.aliammar.net (caddy-apps → `authelia:9091` on `edge`; public via
  cloudflared).
- **Auth mode:** it *is* the auth. A caddy-apps site with `import authelia` asks it. Access rules
  are first-match; `default_policy: deny` plus a last catch-all deny, and each app's PR adds its rule
  above that. The OIDC PR adds the provider, the clients (aiostreams, aiometadata) and the family
  accounts (group `family`).
- **Session:** cookie `authelia_apps_session` on `.aliammar.net`. A different name from admin
  Authelia's `authelia_session`, so the two never overwrite each other; caddy-apps drops the admin
  one before proxying.
- **Data:** `/opt/appdata/authelia` on docker-dmz: `db.sqlite3` (passkeys, TOTP, consent; backup
  class: app data) and `notification.txt` (one-time codes; no mail server).
- **Secrets:** `secret.sops.env`: `AUTHELIA_SESSION_SECRET`, `AUTHELIA_STORAGE_ENCRYPTION_KEY`,
  `AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET` (random, agent-generated).
  `users.sops.yml`: the users with argon2 hashes (Ali; the family with the OIDC PR).
- **Upstream:** [Authelia](https://www.authelia.com/configuration/prologue/introduction/) ·
  [Caddy integration](https://www.authelia.com/integration/proxies/caddy/)

**Gotchas**
- `AUTHELIA_STORAGE_ENCRYPTION_KEY` encrypts the sqlite file, so the two are backed up together.
- A password change = a new hash in `users.sops.yml` (PR); reset by mail is off.
- The code to register a passkey: `sudo cat /opt/appdata/authelia/notification.txt` on docker-dmz.
  Each instance keeps its own passkeys, so register one on `login` too.
- Check a change before its PR: `authelia validate-config` (nixpkgs) on a copy, with stand-in
  secrets in the environment.
