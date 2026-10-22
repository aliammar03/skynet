# gatus

- **Purpose:** the lab's status page and its uptime alerts to `#alerts` (3 failed checks to fire,
  2 passes to clear, a post on recovery too).
- **URL:** https://status.aliammar.net (caddy-admin → `gatus:8080`).
- **Auth mode:** `forward` (Authelia). `^/api/` is open to ops (10.10.90.91) so the agent can read
  it: `curl https://status.aliammar.net/api/v1/endpoints/statuses`.
- **Data:** `/opt/appdata/gatus/data.db` (check history; backup class: disposable).
- **Secrets:** `secret.sops.env`: `DISCORD_ALERTS_WEBHOOK` (the `#alerts` webhook URL, same value as
  `discord_alerts_webhook` in `secrets/docker-admin.yaml`).
- **Upstream:** [Gatus](https://github.com/TwiN/gatus#configuration)

**Checks** (`config/*.yaml`, merged; endpoint lists append)

| Group | What | Passes when |
|---|---|---|
| `door` | each admin site through caddy-admin | `302` to Authelia, cert valid > 7 days (`auth`: `200`) |
| `target` | each upstream's IP:port | TCP connect |
| `dns` | `auth.aliammar.net A` on Technitium .50 and .51 | answer is 10.10.60.60 |

**Gotchas**
- `door` checks resolve names through caddy-admin's `edge` aliases, not DNS. A new admin site needs
  its name added there too.
- `target` checks leave as 10.10.50.40. Upstreams off VLAN 50 need the OPNsense rule for
  `HOST_DOCKER_ADMIN`.
- No healthcheck (the image has no shell). heartbeat pings healthchecks.io only while
  `/health` answers, so a dead Gatus still pages.
