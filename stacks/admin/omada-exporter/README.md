# omada-exporter

- **Purpose:** OmadaBridge (skynetv2.md → P5 → Wider eyes) reads the Omada controller (CT 525,
  Omada 6.2) as a viewer: the controller, each AP and switch (uptime, CPU, memory, radios'
  utilization and interference, ports), site alerts, and the client count. Its Home Assistant side
  (MQTT) and device control are off; per-client metrics too (a series per client, relabelled as it
  roams).
- **URL / auth:** none (not routed). VictoriaMetrics scrapes `omada-exporter:9202` once a minute on
  `edge` (`stacks/admin/metrics/scrape.yaml`); Gatus checks `/healthz`.
- **The controller's user** (Ali, once): Global View → Account → Role: a viewer role (read only);
  Account → Add New User, e.g. `exporter`, with that role and the site, `Omada Network Skynet`.
  Log in once as it to confirm the password. `OMADA_SITE` names the site exactly, so renaming the
  site means changing it too.
- **TLS:** checked against the controller's self-signed cert, caddy-admin's pin (`omada.pem`, name
  `Omada`, mapped to 10.10.50.25:8043). docker-admin shares VLAN 50 with CT 525.
- **Data:** none. Backup class: none.
- **Secrets:** `secret.sops.env` (Ali): `OMADA_USER` and `OMADA_PASS`.
- **Alerts** (`stacks/admin/metrics/rules/network.yml`): `ExporterBlind` when it answers but reports
  no device for 10 minutes (it has no metric for a failed controller call: those are only in its
  log); `TargetDown` when it doesn't answer.
- **Upstream:** [OmadaBridge](https://github.com/RCooLeR/omada_exporter)

**Gotchas**
- It exits when the controller doesn't answer at its start ("App failed to run"), so a controller
  outage is a restart loop (Docker backs off). That's why it's a stack of its own: doco-cd redeploys
  a whole stack when one of its containers dies.
- A re-pinned controller cert changes `omada.pem`; its fingerprint in the `skynet.pinned-cert` label
  must change with it.
- Omada's logs come by syslog (its global Remote Logging: 10.10.50.40, UDP 5516;
  `stacks/admin/logs`), not through this exporter.
