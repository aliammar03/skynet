# exporters

- **Purpose:** exporters for appliances whose API they read with a key of their own
  (skynetv2.md → P5 → Wider eyes), kept apart from `metrics`: doco-cd redeploys a whole stack when
  one of its containers dies, so a crash loop here restarts only these. **opnsense-exporter**
  reads OPNsense's gateways (status, loss, latency), interfaces, firewall counters, pf states,
  mbufs and services.
- **URL / auth:** none (not routed). VictoriaMetrics scrapes `opnsense-exporter:8080` once a minute
  on `edge` (`stacks/admin/metrics/scrape.yaml`); Gatus checks its landing page, which calls no API.
- **OPNsense's API user** (Ali, once; System → Access → Users): a user with no login of its own
  (a scrambled password) and only the pages its collectors read, plus the privilege that denies
  config writes, as ops's `skynet-read`:
  - Diagnostics: Firewall statistics · Diagnostics: Netstat · Reporting: Traffic
  - System: Gateways · System: Status · Status: Services · Lobby: Dashboard

  Of these, only Status: Services allows an action (restarting a service). The exporter's other
  collectors are off (`compose.yaml`), so it calls nothing else: firmware (an upgrade), cron,
  Unbound and Kea (dnsmasq serves DHCP here), the VPNs, CARP, ARP and temperature. Then the user's
  API key: its `apikey.txt` holds `key=` and `secret=`.
- **TLS:** checked against OPNsense's self-signed cert, caddy-admin's pin (`opnsense.pem`, name
  `OPNsense.internal`, mapped to 10.10.50.1). docker-admin reaches OPNsense's API on VLAN 50.
- **Data:** none. Backup class: none.
- **Secrets:** `secret.sops.env` (Ali): `OPNSENSE_EXPORTER_OPS_API_KEY` and
  `OPNSENSE_EXPORTER_OPS_API_SECRET`, from `apikey.txt`.
- **Alerts** (`stacks/admin/metrics/rules/network.yml`): `ExporterBlind` (`opnsense_up` 0 for 10
  minutes: the key, the user's pages or the API), `GatewayDown`, `GatewayLossy`,
  `FirewallStatesHigh`; `TargetDown` when the exporter itself is down.
- **Upstream:** [opnsense-exporter](https://github.com/AthennaMind/opnsense-exporter)

**Gotchas**
- A re-pinned OPNsense cert changes `opnsense.pem`; its fingerprint in the `skynet.pinned-cert`
  label must change with it, so doco-cd recreates the container (Go reads the cert once).
- A wrong key fails every scrape, a few API calls each minute from docker-admin (10.10.50.40). If
  OPNsense's login protection counts those, it blocks that address for a while.
- The image runs as root by default; here as nobody, read-only, with no capabilities.
