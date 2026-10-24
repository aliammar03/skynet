# gatus

- **Purpose:** the lab's status page and its uptime alerts to `#alerts` (3 failed checks to fire,
  2 passes to clear, a post on recovery too).
- **URL:** https://status.aliammar.net (caddy-admin → `gatus:8080`).
- **Auth mode:** `forward` (Authelia). `^/api/` is open to ops (10.10.90.91) so the agent can read
  it: `curl https://status.aliammar.net/api/v1/endpoints/statuses`, and the `dns` suites at
  `/api/v1/suites/statuses`.
- **Data:** `/opt/appdata/gatus/data.db` (check history; backup class: disposable).
- **Secrets:** `secret.sops.env`: `DISCORD_ALERTS_WEBHOOK` (the `#alerts` webhook URL, same value as
  `discord_alerts_webhook` in `secrets/docker-admin.yaml`); `HC_BADGE_URL_ADMIN` (healthchecks.io project
  `skynet` → Badges, 2-state, the `docker-admin` row's JSON URL; it answers
  `{"status": "up", ...}`); `HC_BADGE_URL_DMZ` (the same for the `docker-dmz` row).
- **Upstream:** [Gatus](https://github.com/TwiN/gatus#configuration)

**Checks** (`config/*.yaml`, merged; endpoint lists append), one row per thing, every 60 s unless noted

| Group | What | Passes when |
|---|---|---|
| `door` | `caddy-admin + authelia`: `auth.aliammar.net/api/health` through caddy-admin (Gatus reaches it by caddy-admin's `edge` alias) | `200`, cert valid > 7 days: Caddy, the wildcard cert and Authelia, shared by every admin site |
| `door` | `caddy-apps + authelia`: `login.aliammar.net/api/health` through caddy-apps (10.10.100.35, via Technitium) | `200`, cert valid > 7 days: the apps door and the apps' Authelia |
| `door` | `public`: the same URL resolved through 1.1.1.1, so Cloudflare → tunnel → cloudflared → caddy-apps | `200`: the public path |
| `service` | each admin UI's IP:port (Technitium's are in its suite) | TCP connect |
| `app` | each app on docker-dmz by its name, through caddy-apps | `200` (`302` behind Authelia) |
| `dns` | one **suite** (row) per Technitium server (.50, .51); its steps, each alerting on its own as `<server> <step>`: `ui` (:5380), `zone` (`auth.aliammar.net` A), `AAAA` (same name), `forwarding` (`google.com`), `blocking` (`googlesyndication.com`) | connect; 10.10.60.60; `NOERROR` (no record, not NXDOMAIN); `NOERROR`; `NXDOMAIN` (HaGeZi Pro) |
| `job` | each Docker host's heartbeat badge (`HC_BADGE_URL_ADMIN`, `HC_BADGE_URL_DMZ`), every 5 min, no alert (healthchecks.io alerts) | `status` is `up` |

**Gotchas**
- Suites are alpha in Gatus v5.37. Step names share one namespace with every other check, so each
  carries its server's name. Alerts go on each step (there are no suite-level alerts), and every
  step has `always-run`, so one failure doesn't skip the other checks.
- `service` checks and the apps door row leave as 10.10.50.40; OPNsense rule 235 (`HOST_DOCKER_ADMIN` →
  `ROLE_ADMIN_TARGETS` : `PORT_ADMIN_PROXY`) lets them through. `public` asks 1.1.1.1 directly
  (rule 840).
- `HC_BADGE_URL_ADMIN` and `HC_BADGE_URL_DMZ` must be in `secret.sops.env` before this config deploys: an
  unset variable leaves the row with no URL, and Gatus refuses to start.
- A broken single `sites/<name>.conf` isn't caught here (the door row tests the shared path).
- No healthcheck (the image has no shell). heartbeat pings healthchecks.io only while
  `/health` answers, so a dead Gatus still pages.
