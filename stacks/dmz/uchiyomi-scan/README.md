# uchiyomi-scan

- **Purpose:** asks Uchiyomi to rescan its library folders. Uchiyomi scans only when asked (its
  Tasks list: "on demand"), and CLU files new comics into one of its folders. Every 30 minutes a
  doco-cd scheduled job posts `/api/refresh`, so what CLU files shows within half an hour.
- **URL:** none (not routed).
- **Auth mode:** none.
- **Data:** none.
- **Secrets:** `secret.sops.env`: `UCHIYOMI_TOKEN`, Ali's API token (Uchiyomi → Profile →
  Connections → API tokens: read + write, not admin; a rescan is a POST, which a read-only token
  can't make).
- **Upstream:** [curlimages/curl](https://hub.docker.com/r/curlimages/curl) ·
  [doco-cd job scheduling](https://doco.cd/latest/Advanced/Job-Scheduling/) ·
  Uchiyomi: `stacks/dmz/uchiyomi`

**Gotchas**
- A job is a stack of its own, with reconciliation off (`.doco-cd.yml`; `stacks/README.md` → The
  folder): no `restart` policy and no healthcheck.
- It reaches Uchiyomi through caddy-apps, at `https://uchiyomi.aliammar.net`: the name is the
  door's alias on `edge` (`stacks/dmz/caddy-apps/compose.yaml`). Uchiyomi's own network stays its
  own.
- Uchiyomi rescans at most once a minute, whoever asks.
- Alerts: doco-cd (via Apprise) when a run fails, which it does while Uchiyomi or the door is
  down.
