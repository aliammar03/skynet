# gatus

- **Purpose:** the lab's status page and its uptime alerts to `#alerts` (3 failed checks to fire,
  2 passes to clear, a post on recovery too).
- **URL:** https://status.aliammar.net (caddy-admin → `gatus:8080`).
- **Auth mode:** `forward` (Authelia). `^/api/` is open to ops (10.10.90.91) so the agent can read
  it: `curl https://status.aliammar.net/api/v1/endpoints/statuses`.
- **Data:** `/opt/appdata/gatus/data.db` (check history; backup class: disposable).
- **Secrets:** `secret.sops.env`: `DISCORD_ALERTS_WEBHOOK` (the `#alerts` webhook URL, same value as
  `discord_alerts_webhook` in `secrets/docker-admin.yaml`); `HC_BADGE_URL` (healthchecks.io project
  `skynet` → Badges, 2-state, the `docker-admin` row's JSON URL; it answers
  `{"status": "up", ...}`).
- **Upstream:** [Gatus](https://github.com/TwiN/gatus#configuration)

**Checks** (`config/*.yaml`, merged; endpoint lists append), one row per thing, every 60 s unless noted

| Group | What | Passes when |
|---|---|---|
| `door` | `auth.aliammar.net/api/health` through caddy-admin (Gatus reaches it by caddy-admin's `edge` alias) | `200`, cert valid > 7 days: Caddy, the wildcard cert and Authelia, shared by every admin site |
| `service` | each admin UI's IP:port | TCP connect |
| `dns` | `auth.aliammar.net A` on Technitium .50 and .51 | answer is 10.10.60.60 |
| `dns` | per new Technitium VM, at its build IP until its cutover (P2): `auth.aliammar.net`, `google.com`, `googlesyndication.com` | 10.10.60.60; `NOERROR` (forwarding); `NXDOMAIN` (blocking, HaGeZi Pro) |
| `job` | heartbeat's healthchecks.io badge (`HC_BADGE_URL`), every 5 min, no alert (healthchecks.io alerts) | `status` is `up` |

**Gotchas**
- `service` checks leave as 10.10.50.40; OPNsense rule 235 (`HOST_DOCKER_ADMIN` →
  `ROLE_ADMIN_TARGETS` : `PORT_ADMIN_PROXY`) lets them through.
- `HC_BADGE_URL` must be in `secret.sops.env` before this config deploys: an unset variable leaves
  the row with no URL, and Gatus refuses to start.
- A broken single `sites/<name>.conf` isn't caught here (the door row tests the shared path).
- No healthcheck (the image has no shell). heartbeat pings healthchecks.io only while
  `/health` answers, so a dead Gatus still pages.
