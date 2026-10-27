# logs

- **Purpose:** VictoriaLogs, every host's journal in one place, containers' logs included (Docker's
  journald driver), kept 30 days and never more than 4 GiB. Each host ships with
  `systemd-journal-upload` (`modules/observability.nix`; PBS from `pbs/etc/`, the Proxmox nodes from
  `pve/etc/`), which keeps a cursor: after an outage it resumes where it stopped, and until then the
  host's own journal (2 weeks) holds the logs. Appliances log by syslog (OPNsense). **vmalert-logs** runs `rules/*.yml` (LogsQL; vmalert adds `_time:<interval>` to a
  query without its own) and sends what fires to Alertmanager. Its alerts' state lives in
  VictoriaMetrics and comes back on its first evaluation only, so it starts once both stores
  answer. **mcp-victorialogs** is the agent's eyes: VictoriaLogs' query tools over MCP (streamable
  HTTP), which only read. Its documentation search is off (its index was most of its memory).
- **URL:** https://logs.aliammar.net (caddy-admin → `victorialogs:9428`): the query UI at
  `/select/vmui`; vmalert-logs' rules and pending alerts at `/select/vmalert/` (VictoriaLogs
  proxies it). `/mcp` goes to `mcp-victorialogs:8081` (`.mcp.json`'s `victorialogs`). Grafana
  (`stacks/admin/grafana`) reads VictoriaLogs by name on `edge`, through its plugin.
- **Rules** (`rules/logs.yml`, LogsQL): `CrashLoop` (systemd's line for each container start),
  `LogsNotArriving` (each host's `log-heartbeat` line, every 5 minutes, missing for 15),
  `SyslogNotArriving` (OPNsense's lines, missing for 15), `GuestBackupFailed` (a Proxmox node's
  vzdump error), `FilesystemErrors`, `LogFlood` and `LogsDropped` (journald's own count of what it
  dropped).
- **Auth mode:** `forward` (Authelia). Ops (10.10.90.91) reads `/select/logsql/` without a login:
  `curl -s https://logs.aliammar.net/select/logsql/query --data-urlencode 'query=_time:1h CONTAINER_NAME:doco-cd'`.
  And `/mcp`, the MCP server's tools, which only read. Deletes are off in VictoriaLogs itself.
- **The way in:** `vlagent` on :9429, on the host's network, so docker-admin's firewall admits only
  the hosts that ship (`hosts/docker-admin/default.nix`), after OPNsense's `ROLE_LOG_SHIPPERS`.
  It forwards to VictoriaLogs on `127.0.0.1:9428`, which nothing off this host reaches. vlagent has
  no query API: a host that ships its journal reads no one's logs, its own included.
- **Streams:** `_HOSTNAME`, `_SYSTEMD_UNIT` and `CONTAINER_NAME` (with `_MACHINE_ID`), so each
  container is a stream of its own. Every other journal field is kept as a field (`PRIORITY` also
  becomes `level`).
- **Syslog** (vlagent's listeners, on the host's network): TCP 5514, OPNsense's (System → Settings
  → Logging → Remote, RFC 5424), admitted from 10.10.50.1 only. Its lines carry `hostname`,
  `app_name` (the stream, with `proc_id`), `format`, `severity` (also as `level`) and their own
  time. The firewall log (`app_name:=filterlog`) is OPNsense's CSV; what got blocked, and where:
  ```
  _time:1h app_name:=filterlog ",block," | extract_regexp "^(?P<rule>[^,]*),[^,]*,[^,]*,(?P<rid>[^,]*),(?P<iface>[^,]*),[^,]*,(?P<action>[^,]*),(?P<dir>[^,]*),4,(?:[^,]*,){7}(?P<proto>[^,]*),[^,]*,(?P<src>[^,]*),(?P<dst>[^,]*),(?P<sport>[^,]*),(?P<dport>[^,]*)" | stats by (iface, src, dst, dport) count() as blocks | sort by (blocks desc) | limit 20
  ```
  (IPv4 only; an ICMP line has no ports there.)
- **Data:** `/opt/appdata/logs/data` (the logs) and `/opt/appdata/logs/buffer` (vlagent's, while
  VictoriaLogs is down; at most 1 GiB, oldest dropped first). Backup class: cache.
- **Memory:** at most 1 GiB (`mem_limit`); its caches stay under 256 MiB. docker-admin has no swap,
  so past the limit the kernel kills VictoriaLogs and Docker restarts it.
- **Secrets:** none.
- **Upstream:** [VictoriaLogs](https://docs.victoriametrics.com/victorialogs/) ·
  [vlagent](https://docs.victoriametrics.com/victorialogs/vlagent/) ·
  [journald ingestion](https://docs.victoriametrics.com/victorialogs/data-ingestion/journald/) ·
  [LogsQL](https://docs.victoriametrics.com/victorialogs/logsql/)

**Gotchas**
- A new host's first upload sends its whole journal (up to 2 weeks); older than 30 days is dropped.
- Floods: journald on each host drops what one service logs past about 100 lines a second
  (`modules/observability.nix`), and `LogFlood` alerts at 50. Every container's lines come from
  dockerd, so containers share one allowance and a flooding one costs its neighbours lines too:
  `LogsDropped` reports them. A host that sends past journald (a compromised one) could still fill
  the store: past 4 GiB the oldest days go, and each host's own journal still holds its two weeks.
- `LogsNotArriving` knows a host from its heartbeats this week: a new host counts from its first
  heartbeat, and one silent for a week drops out of the rule (HostDown has it by then).
- vlagent's port also serves `/metrics` and the usual `/debug/pprof` to the hosts that ship; its
  flags hold no secret.
- OPNsense's firewall log is the biggest source: about 8 lines a second (2026-10-28), most of them
  the default rule passing the firewall's own traffic.
- No healthcheck in VictoriaLogs or vlagent (the images are only the binary): Gatus checks both
  `/health` endpoints, and VictoriaMetrics scrapes both. vmalert-logs has one.
- A LogsQL rule's labels are its `stats by (...)` fields; each rule sets `instance` from
  `_HOSTNAME`, so Alertmanager groups and inhibits it like a metrics rule. CI checks `rules/` with
  the pinned vmalert's `-dryRun`.
