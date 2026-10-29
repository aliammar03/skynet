# authelia (apps)

- **Purpose:** the apps' login portal and forward-auth for caddy-apps, separate from admin Authelia
  (`stacks/admin/authelia`): its own users, sessions and secrets. It's reachable from the internet
  through the tunnel, so it lives in the DMZ with the apps it guards (D4).
- **URL:** https://login.aliammar.net (caddy-apps → `authelia:9091` on `edge`; public via
  cloudflared).
- **Auth mode:** it *is* the auth. A caddy-apps site with `import authelia` asks it. Access rules
  are first-match; `default_policy: deny` plus a last catch-all deny, and each app's PR adds its rule
  above that. Now: calibre, sillytavern and marinara for group `admins`, with a password
  (`one_factor`).
- **OIDC provider** (issuer `https://login.aliammar.net`), for aiostreams, aiometadata, komga and
  uchiyomi:
  - `oidc-clients.yml`: the clients (secrets as pbkdf2 digests); policies `apps` (a password from
    `admins` or `family`: the two addons) and `admins` (a password from `admins` alone: Komga and
    Uchiyomi); claims policy `apps` (`preferred_username`, `groups`, … in the ID token too);
  - `oidc.sops.yml`: the provider's HMAC secret and RS256 signing key (agent-generated);
  - each app's plaintext client secret: its `oidc.sops.env` (agent-generated).

  `X_AUTHELIA_CONFIG` merges the three files. The client list lives in one file only: a second
  file's `clients` would replace it, not add to it.
- **Session:** cookie `authelia_apps_session` on `.aliammar.net`. A different name from admin
  Authelia's `authelia_session`, so the two never overwrite each other. caddy-apps passes it only to
  this instance (`login` and its forward-auth checks), never to an app, and drops the admin one.
- **Data:** `/opt/appdata/authelia` on docker-dmz: `db.sqlite3` (passkeys, TOTP, consent; backup
  class: app data) and `notification.txt` (one-time codes; no mail server).
- **Secrets:** `secret.sops.env`: `AUTHELIA_SESSION_SECRET`, `AUTHELIA_STORAGE_ENCRYPTION_KEY`,
  `AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET` (random, agent-generated).
  `users.sops.yml`: the users with argon2 hashes: Ali in `admins`, the family in `family` (with their
  Authentik usernames, because both addons name accounts by `preferred_username`).
- **Upstream:** [Authelia](https://www.authelia.com/configuration/prologue/introduction/) ·
  [Caddy integration](https://www.authelia.com/integration/proxies/caddy/)

**Gotchas**
- `AUTHELIA_STORAGE_ENCRYPTION_KEY` encrypts the sqlite file, so the two are backed up together.
- A password change = a new hash in `users.sops.yml` (PR); reset by mail is off.
- The code to register a passkey: `sudo cat /opt/appdata/authelia/notification.txt` on docker-dmz.
  Each instance keeps its own passkeys, so register one on `login` too.
- A new OIDC client: its secret with `authelia crypto hash generate pbkdf2 --variant sha512`, the
  digest here, the plaintext in the app's own `oidc.sops.env`, both in one command so the value is
  never shown.
- Check a change before its PR: `authelia validate-config` (nixpkgs) on a copy, with stand-in
  secrets in the environment.
