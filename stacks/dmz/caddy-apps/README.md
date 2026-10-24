# caddy-apps

- **Purpose:** the apps door. One wildcard site `*.aliammar.net` (cert via Cloudflare DNS-01) in
  front of the apps on docker-dmz; unknown names get 404. cloudflared hands it the public names.
- **DNS-01 without a propagation check** (the site's `tls` block), as on caddy-admin: inside the lab
  Technitium answers for `aliammar.net` itself, so Caddy waits 60 s and Let's Encrypt checks
  Cloudflare. Gatus's `caddy-apps + authelia` row alerts within 7 days of expiry.
- **Where:** macvlan `dmz`, 10.10.100.35, OPNsense alias `HOST_PROXY_APPS` (rules 200 app clients →
  :80/:443, 430 → Home Assistant, 235 Gatus → doors, 830 → DNS; 810 web egress). Also on `edge`,
  where it reaches the apps and the apps' Authelia by container name.
- **Auth mode:** a site with `import authelia` asks the apps' Authelia (`stacks/dmz/authelia`, portal
  `login`), never the admin one. The site-wide `request_header` drops admin Authelia's cookie
  (`authelia_session`, scoped to `.aliammar.net`), so no app sees an admin session.
- **Files:** `conf/` is mounted at `/etc/caddy` (no secrets in it): `Caddyfile` and
  `sites/<name>.conf` (one per name). A route edit reloads in place (`recreate.ignore` + `--watch`).
- **Data:** `/opt/appdata/caddy-apps/{data,config}`: certs and ACME account. Re-issuable; no backup
  needed.
- **Secrets** (`secret.sops.env`): `CLOUDFLARE_API_TOKEN` (Zone → DNS → Edit, `aliammar.net` only;
  its own token, not caddy-admin's).
- **Upstream:** [caddybuilds/caddy-cloudflare](https://github.com/caddybuilds/caddy-cloudflare) ·
  [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)

| Site | Upstream | Auth |
|---|---|---|
| login | authelia:9091 (`edge`) | it *is* the login |
| homeassistant | http://10.10.30.50:80 | own (Home Assistant trusts this door as its proxy) |

**Gotchas**
- Public requests come from cloudflared (10.10.100.33) over the macvlan. Caddy trusts only that IP
  for `Cf-Connecting-Ip`, so its logs and the upstreams see the visitor's address.
- `gw_priority` puts the default route on `dmz`. Without it, replies to clients could leave via
  Docker's bridge and be NATed to the host's IP.
- HTTP/3 stays off (`protocols h1 h2`): Obsidian LiveSync's clients misbehave over it.
