# grafana

- **Purpose:** dashboards over VictoriaMetrics and VictoriaLogs (`skynetv2.md` → P5 → Grafana).
  Everything it shows comes from git: the data sources (`provisioning/datasources/`) and the boards
  (`dashboards/`), read-only in the UI, so a change is a PR. The stores' own UIs stay for ad-hoc
  queries (`metrics.aliammar.net/vmui`, `logs.aliammar.net/select/vmui`).
- **URL:** https://grafana.aliammar.net (caddy-admin → `grafana:3000` on `edge`).
- **Auth mode:** `forward` (Authelia) at the door, then OIDC: Grafana sends you straight to admin
  Authelia's client `grafana` and makes you its admin (`GrafanaAdmin`). Nobody else gets a token
  for that client. **Break-glass:** https://grafana.aliammar.net/login?disableAutoLogin shows the
  login form; user `admin`, its password with
  `nix shell nixpkgs#sops -c sops -d stacks/admin/grafana/secret.sops.env | grep ^GF_SECURITY_ADMIN_PASSWORD=`.
- **Boards** (folder per subfolder of `dashboards/`):
  - `lab/`, ours:
    - **Live:** the lab right now, every 10 s over 15 minutes: targets down, alerts firing,
      containers, backup age, PBS's datastore, log lines; CPU, memory, network and disk per host
      (a Host picker); the busiest containers; Proxmox guests; and every host's errors and
      warnings, newest first.
    - **Backups:** each guest's newest PBS backup, verify state and count; their age over the week;
      the datastore; the app backups (restic) per host; PBS's copy to Drive; docker-dmz's snapshots;
      the backup jobs' errors.
  - `upstream/`, grafana.com's at pinned revisions (`dashboards/fetch.sh`): Node Exporter Full,
    cAdvisor (by compose project and container), Proxmox, VictoriaMetrics, VictoriaLogs, vmalert,
    Alertmanager.
- **Live tail:** Explore → VictoriaLogs → **Live** follows a LogsQL query as lines arrive (Grafana
  Live, a websocket through the door).
- **Data:** `/opt/appdata/grafana/data` (its database, sessions, the plugin). Backup class: cache:
  all of it comes from git or your login. Grafana runs as 472; docker-admin's config gives it the
  folder (`hosts/docker-admin/default.nix`).
- **Plugins:** Grafana 13 ships no data sources; it fetches them from grafana.com. Two, before it
  starts (`GF_PLUGINS_PREINSTALL_SYNC`): VictoriaLogs' `victoriametrics-logs-datasource` (its
  version pinned there) and Grafana's own `prometheus` (at Grafana's version). Its default list of
  18 others, fetched in the background, is off (`GF_PLUGINS_PREINSTALL` empty). They stay in the
  data folder, so a restart needs grafana.com only when a version changes.
- **Secrets:** `secret.sops.env`: `GF_SECURITY_ADMIN_PASSWORD` (the break-glass).
  `oidc.sops.env`: `GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET`, whose digest is in
  `stacks/admin/authelia/oidc-clients.yml`. Both agent-generated.
- **Upstream:** [Grafana](https://grafana.com/docs/grafana/latest/) ·
  [provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/) ·
  [Authelia's Grafana guide](https://www.authelia.com/integration/openid-connect/clients/grafana/) ·
  [VictoriaLogs data source](https://docs.victoriametrics.com/victorialogs/victorialogs-datasource/)

**Gotchas**
- A board edited in the UI can't be saved (`allowUiUpdates: false`). Export its JSON, put it in
  `dashboards/lab/`, PR.
- `fetch.sh` refetches the upstream boards at the revisions it names, pointing any data source
  input that no template variable stands for at `victoriametrics`. A newer revision is a new number
  there, then a run and a PR.
- The plugin's version isn't Renovate's: bump `GF_PLUGINS_PREINSTALL_SYNC` by hand, from its
  [releases](https://github.com/VictoriaMetrics/victorialogs-datasource/releases).
- Grafana reaches `auth.aliammar.net` on `edge` (caddy-admin's alias), not through DNS: docker-admin
  can't reach its own macvlan address.
- VictoriaMetrics scrapes every 30 s, so a Live line moves at that pace; 5 s refresh only redraws.
