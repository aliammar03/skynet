# alertmanager

- **Purpose:** posts vmalert's alerts to Discord `#alerts` (`skynetv2.md` → P5 → Alerts): the
  rules are in `stacks/admin/metrics/rules/` and `stacks/admin/logs/rules/`. One post per alert and
  host ("Firing: DiskFull on docker-dmz", one line per alert), the same again when it resolves, and
  a reminder every 12 hours while it fires. A host that's down (`HostDown`) mutes its own other
  alerts.
- **Watchdog:** always firing; every minute it goes to healthchecks.io's check `alertmanager`
  (period 1 min, grace 10 min), which posts to `#alerts` when the pings stop: vmalert, Alertmanager,
  docker-admin or its egress down.
- **DeliveryWatchdog:** firing only while Discord takes the posts: Gatus's `discord webhook` row
  finds the webhook, and no post to Discord failed in 15 minutes. Every minute it goes to check
  `alerts-delivery` (period 1 min, grace 10 min). A deleted webhook or failing posts stop it, and
  healthchecks.io posts through its own integrations, not the lab's webhook (email on these two
  checks reaches Ali even when Discord is down).
- **URL:** https://alerts.aliammar.net (caddy-admin → `alertmanager:9093`): alerts, silences.
- **Auth mode:** `forward` (Authelia). Ops (10.10.90.91) reaches the API without a login only to
  read (`GET /api/v2/alerts`, `/silences`, `/status`), set a silence (`POST /api/v2/silences`) and
  expire one (`DELETE /api/v2/silence/<id>`): the agent's silences verb (`AGENTS.md`, Rule 4).
- **Data:** `/opt/appdata/alertmanager/data`: silences and the notification log (backup class:
  data). It runs as `nobody`, so docker-admin's config gives it the folder
  (`hosts/docker-admin/default.nix`).
- **Secrets:** `secret.sops.env`: `DISCORD_ALERTS_WEBHOOK` (the `#alerts` webhook URL, Gatus's
  same value), `HC_PING_URL` (check `alertmanager`'s ping URL) and `HC_DELIVERY_PING_URL` (check
  `alerts-delivery`'s). Alertmanager reads secrets only from files, so the entrypoint writes them
  onto a tmpfs before it starts.
- **Upstream:** [Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/) ·
  [vmalert](https://docs.victoriametrics.com/victoriametrics/vmalert/)

**Gotchas**
- A silence from the API: `curl -s https://alerts.aliammar.net/api/v2/silences -H 'Content-Type: application/json' -d '{"matchers":[{"name":"instance","value":"docker-dmz","isRegex":false}],"startsAt":"<now>","endsAt":"<within 4 h>","createdBy":"agent","comment":"<the work>"}'`.
- CI checks `alertmanager.yml` with the pinned image's `amtool check-config`.
- A failed post to Discord shows as `AlertmanagerSendFailing`, which can't reach Discord either:
  the agent and the dashboards see it, and `DeliveryWatchdog` stops, so healthchecks.io posts.
