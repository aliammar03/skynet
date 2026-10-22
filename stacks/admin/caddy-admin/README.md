# caddy-admin

- **Purpose:** the admin door. One wildcard site `*.aliammar.net` (cert via Cloudflare DNS-01) in
  front of the lab's admin UIs; unknown names get 404.
- **Where:** macvlan `adm60`, 10.10.60.60, in OPNsense alias `HOST_PROXY_ADMIN` (rules 210 admin
  clients + ops → :443, 230 → admin targets, 830 → DNS; 810 web egress). Also on `edge` for apps.
- **Auth mode:** `forward`: every site except `auth` passes an Authelia login first, then the
  upstream's own login. Direct IPs bypass Caddy and stay the break-glass path.
- **Files:** `conf/` is mounted at `/etc/caddy` (no secrets in it): `Caddyfile`, `sites/<name>.conf`
  (one per name), `certs/` (the upstreams' public certs). A route edit reloads in place
  (`recreate.ignore` + `--watch`).
- **Data:** `/opt/appdata/caddy-admin/{data,config}`: certs and ACME account. Re-issuable; no backup
  needed.
- **Secrets** (`secret.sops.env`): `CLOUDFLARE_API_TOKEN` (Zone → DNS → Edit, `aliammar.net` only).
- **Upstream:** [caddybuilds/caddy-cloudflare](https://github.com/caddybuilds/caddy-cloudflare) ·
  [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)

| Site | Upstream | TLS to upstream |
|---|---|---|
| opnsense | https://10.10.50.1 | pinned self-signed `certs/opnsense.pem`, name `OPNsense.internal` |
| proxmox-core / -network | https://10.10.50.11:8006 / .10:8006 | each node's `pve-root-ca.pem` |
| pbs | https://10.10.20.40:8007 | pinned self-signed `certs/pbs.pem`, name `lxc-proxmox-backup-server` |
| omada | https://10.10.50.25:8043 | pinned self-signed `certs/omada.pem`, name `Omada` |
| technitium-core / -network | http://10.10.70.51:5380 / .50:5380 | none |
| unraid | http://10.10.20.20 | none |
| auth / status | authelia:9091 / gatus:8080 (`edge`) | none |

**Gotchas**
- A regenerated appliance cert (OPNsense, PBS or Omada after a reset or an update) breaks its site
  with a TLS error in the log. Re-pin with
  `openssl s_client -connect <ip:port> </dev/null | openssl x509 > conf/certs/<name>.pem` (PR).
- OPNsense rejects proxied logins unless System → Settings → Administration → Alternate Hostnames
  lists `opnsense.aliammar.net`.
- A new site also needs its name in the `edge` aliases in `compose.yaml`, so Gatus can check it.
- Unraid redirects to absolute `http://` URLs; `header_down Location` rewrites them to https.
- `gw_priority` puts the default route on `adm60`. Without it, replies to clients could leave via
  Docker's bridge and be NATed to the host's IP.
