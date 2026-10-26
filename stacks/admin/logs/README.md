# logs

- **Purpose:** VictoriaLogs, every host's journal in one place, containers' logs included (Docker's
  journald driver), kept 30 days and never more than 4 GiB. Each host ships with
  `systemd-journal-upload` (`modules/observability.nix`; PBS from `pbs/etc/`), which keeps a cursor:
  after an outage it resumes where it stopped, and until then the host's own journal (2 weeks) holds
  the logs. **vmalert-logs** runs `rules/*.yml` (LogsQL; vmalert adds `_time:<interval>` to a
  query without its own) and sends what fires to Alertmanager; `logs.yml` has `CrashLoop`,
  `FilesystemErrors` and `LogFlood`. The agent's MCP server joins this stack in a later P5 PR.
- **URL:** https://logs.aliammar.net (caddy-admin → `victorialogs:9428`): the query UI at
  `/select/vmui`.
- **Auth mode:** `forward` (Authelia). Ops (10.10.90.91) reads `/select/logsql/` without a login:
  `curl -s https://logs.aliammar.net/select/logsql/query --data-urlencode 'query=_time:1h CONTAINER_NAME:doco-cd'`.
  Deletes are off in VictoriaLogs itself.
- **The way in:** `vlagent` on :9429, on the host's network, so docker-admin's firewall admits only
  the hosts that ship (`hosts/docker-admin/default.nix`), after OPNsense's `ROLE_LOG_SHIPPERS`.
  It forwards to VictoriaLogs on `127.0.0.1:9428`, which nothing off this host reaches. vlagent has
  no query API: a host that ships its journal reads no one's logs, its own included.
- **Streams:** `_HOSTNAME`, `_SYSTEMD_UNIT` and `CONTAINER_NAME` (with `_MACHINE_ID`), so each
  container is a stream of its own. Every other journal field is kept as a field (`PRIORITY` also
  becomes `level`).
- **Data:** `/opt/appdata/logs/data` (the logs) and `/opt/appdata/logs/buffer` (vlagent's, while
  VictoriaLogs is down; at most 1 GiB, oldest dropped first). Backup class: cache.
- **Secrets:** none.
- **Upstream:** [VictoriaLogs](https://docs.victoriametrics.com/victorialogs/) ·
  [vlagent](https://docs.victoriametrics.com/victorialogs/vlagent/) ·
  [journald ingestion](https://docs.victoriametrics.com/victorialogs/data-ingestion/journald/) ·
  [LogsQL](https://docs.victoriametrics.com/victorialogs/logsql/)

**Gotchas**
- A new host's first upload sends its whole journal (up to 2 weeks); older than 30 days is dropped.
- Floods: journald on each host drops what one service logs past about 100 lines a second
  (`modules/observability.nix`), and `LogFlood` alerts at 50. A host that sends past journald (a
  compromised one) could still fill the store: past 4 GiB the oldest days go, and each host's own
  journal still holds its two weeks.
- vlagent's port also serves `/metrics` and the usual `/debug/pprof` to the hosts that ship; its
  flags hold no secret.
- No healthcheck in VictoriaLogs or vlagent (the images are only the binary): Gatus checks both
  `/health` endpoints, and VictoriaMetrics scrapes both. vmalert-logs has one.
- A LogsQL rule's labels are its `stats by (...)` fields; each rule sets `instance` from
  `_HOSTNAME`, so Alertmanager groups and inhibits it like a metrics rule. CI checks `rules/` with
  the pinned vmalert's `-dryRun`.
