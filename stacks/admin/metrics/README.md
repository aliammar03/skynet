# metrics

- **Purpose:** VictoriaMetrics, the lab's metrics: every host, container, backup job and deploy
  tool, scraped every 30 s from `scrape.yaml` and kept 13 months. Proxmox (once a minute) and PBS
  (every 5 minutes) come through their exporters. Alerts and the agent's MCP server join this stack
  in later P5 PRs (`skynetv2.md` → P5).
- **URL:** https://metrics.aliammar.net (caddy-admin → `victoriametrics:8428`): the query UI at
  `/vmui`, the scrape targets at `/targets`.
- **Auth mode:** `forward` (Authelia). Ops (10.10.90.91) reads the query API without a login, only
  its read paths (`/api/v1/query`, `query_range`, `series`, `labels`, `label/…/values`, `metadata`,
  `targets`, `status/…`, `export`): `curl -s 'https://metrics.aliammar.net/api/v1/query?query=up'`.
  Nothing that writes or deletes is open.
- **Data:** `/opt/appdata/metrics/data` (the history; backup class: cache, not backed up). About
  30–45 MB a day, so 12–18 GB at 13 months.
- **Secrets:** `pve.sops.yml`: one module per Proxmox node (`core`, `network`), with token
  `skynet@pve!metrics` (PVEAuditor on `/`) and its `token_value`, the only encrypted key (Ali).
  `secret.sops.env`: `PBS_API_TOKEN`, the secret of PBS's `metrics@pbs!exporter` (audit on the
  datastore and the host; Ali).
- **Targets** (`scrape.yaml`; `instance` is the host's name):

  | Job | Where | What |
  |---|---|---|
  | `node` | every host :9100 | node-exporter: the host, its failed units, and job results from `/var/lib/node-exporter/*.prom` |
  | `comin` | every NixOS host :4243 | fetch, build and deploy failures; `comin_need_to_reboot` |
  | `cadvisor` | both Docker hosts :9338 | each container's CPU, memory, network and disk I/O, with its compose project |
  | `doco-cd` | both Docker hosts :9120 | polls, deploys, scheduled jobs |
  | `gatus` | `gatus:8080` | each row's result, response time and certificate expiry |
  | `pve` | `pve-exporter:9221`, one module per node | guests, storage, backups-job coverage |
  | `pbs` | `pbs-exporter:10019` | each guest's newest backup and its verify (`pbs_snapshot_vm_last_timestamp`, `pbs_snapshot_vm_last_verify`), the datastore's size |
  | `victoriametrics`, `victorialogs`, `vlagent` | this host | the stack itself |

- **Job results** (node-exporter's textfile collector): `resticprofile_backup_*` from each Docker
  host's nightly backup (`restic-appdata.prom`), `skynet_pbs_offsite_*` from the offsite sync
  (docker-admin), `skynet_appdata_snapshot_timestamp_seconds` from btrbk (docker-dmz).
- **Upstream:** [VictoriaMetrics](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/) ·
  [prometheus-pve-exporter](https://github.com/prometheus-pve/prometheus-pve-exporter) ·
  [pbs-exporter](https://github.com/natrontech/pbs-exporter)

**Gotchas**
- A scrape config change recreates VictoriaMetrics (a few seconds without scrapes). CI checks the
  file first with the pinned image's `-dryRun`, which also rejects unknown fields.
- The exporters check TLS against caddy-admin's pins (`../caddy-admin/certs`, mounted whole): the
  nodes' CAs (pve-exporter reads them on every scrape) and PBS's self-signed cert, by its name
  `pbs` (`extra_hosts`). Go reads PBS's only at start, so the `skynet.pinned-cert` label carries its
  fingerprint: a re-pinned `pbs.pem` must change the label in the same PR, which recreates
  pbs-exporter.
- The host firewalls admit only docker-admin to the exporters; on docker-admin its own containers
  come from a Docker bridge (`hosts/docker-admin/default.nix`). A new host joins `scrape.yaml`,
  OPNsense's `ROLE_METRICS_TARGETS` and `ROLE_LOG_SHIPPERS`, and docker-admin's list of log shippers.
- No healthcheck for pbs-exporter (the image is only the binary): its `up` and `pbs_up` series say
  whether it works.
