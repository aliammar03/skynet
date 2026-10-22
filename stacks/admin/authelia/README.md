# authelia

- **Purpose:** SSO portal and forward-auth for the doors. A site with `import authelia` in its
  `caddy.conf` (or `sites/<name>.conf` on caddy-admin) needs a login: passkey + password
  (`two_factor`). Everything not listed in `access_control` is denied.
- **URL:** https://auth.aliammar.net (caddy-admin → `authelia:9091` on `edge`).
- **Auth mode:** it *is* the auth.
- **Data:** `/opt/appdata/authelia`: `db.sqlite3` (passkeys, TOTP, consent; backup class: app data)
  and `notification.txt` (the one-time codes, since there is no mail server yet).
- **Secrets:** `secret.sops.env`: `AUTHELIA_SESSION_SECRET`, `AUTHELIA_STORAGE_ENCRYPTION_KEY`,
  `AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET` (random, agent-generated).
  `users.sops.yml`: the user list with argon2 hashes (Ali).
- **Upstream:** [Authelia](https://www.authelia.com/configuration/prologue/introduction/) ·
  [Caddy integration](https://www.authelia.com/integration/proxies/caddy/)

**Gotchas**
- `AUTHELIA_STORAGE_ENCRYPTION_KEY` encrypts the sqlite file. Without that key, a restored
  `db.sqlite3` is useless, so the two are backed up together.
- Changing a password = a new hash in `users.sops.yml` (PR); reset by mail is off.
- The code to register a passkey: `sudo cat /opt/appdata/authelia/notification.txt` on docker-admin.
- Break-glass: every admin UI still answers on its own IP.
