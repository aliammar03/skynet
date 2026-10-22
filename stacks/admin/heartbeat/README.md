# heartbeat

- **Purpose:** dead-man for docker-admin and for Gatus (the watcher). Every 5 min a doco-cd
  scheduled job pings healthchecks.io check `docker-admin` (project `skynet`, period 5 min, grace
  5 min), but only if `http://gatus:8080/health` answers.
- **URL / auth:** none (not routed).
- **Data:** none.
- **Secrets** (`secret.sops.env`): `HC_PING_URL`.
- **Upstream:** [curlimages/curl](https://hub.docker.com/r/curlimages/curl) ·
  [doco-cd job scheduling](https://doco.cd/latest/Advanced/Job-Scheduling/)
- **Gotchas:**
  - A job is the exception to the stack contract: no `restart` policy (doco-cd requires none; it
    starts the container on schedule) and no healthcheck (it exits after each ping).
  - `.doco-cd.yml` turns reconciliation off for this stack: a stopped job container would otherwise
    count as missing and be redeployed (with a `#alerts` notice) on every poll.
  - Alerts: healthchecks.io when pings stop; doco-cd (via Apprise) when a run fails.
