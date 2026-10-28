# caddy-apps

- **Purpose:** the apps door. One wildcard site `*.aliammar.net` (cert via Cloudflare DNS-01) in
  front of the apps on docker-dmz; unknown names get 404. cloudflared hands it the public names.
- **DNS-01 without a propagation check** (the site's `tls` block), as on caddy-admin: inside the lab
  Technitium answers for `aliammar.net` itself, so Caddy waits 60 s and Let's Encrypt checks
  Cloudflare. Gatus's `caddy-apps + authelia` row alerts within 7 days of expiry.
- **Where:** macvlan `dmz`, 10.10.100.35, OPNsense alias `HOST_PROXY_APPS` (rules 200 app clients →
  :80/:443, 430 → Home Assistant, 235 Gatus → doors, 830 → DNS; 810 web egress). Also on `edge`,
  where it reaches the apps and the apps' Authelia by container name. The apps on the macvlan it
  reaches there, and calibre on `door-calibre`, a network only the two share.
- **Auth mode:** a site with `import authelia` asks the apps' Authelia (`stacks/dmz/authelia`, portal
  `login`), never the admin one. Both Authelias' session cookies are scoped to `.aliammar.net`, so
  browsers send them to every app. The site drops admin Authelia's (`authelia_session`) from every
  request, and the apps' one (`authelia_apps_session`) from every name but `login`, after saving it
  (`vars`) for the `authelia` snippet's check. No app sees a session it could replay.
- **Files:** `conf/` is mounted at `/etc/caddy` (no secrets in it): `Caddyfile` and
  `sites/<name>.conf` (one per name). A route edit reloads in place (`recreate.ignore` + `--watch`).
- **Access log** (the `access_log` snippet, as on caddy-admin): one JSON line per request on stdout,
  so in the host's journal and VictoriaLogs (`CONTAINER_NAME:=caddy-apps`): host, method, status,
  duration, size, and the URI's first path segment only. No headers, query or client address: the
  Stremio addons carry their config in the path. Per app, e.g.
  `_time:1h CONTAINER_NAME:=caddy-apps | unpack_json fields (request.host, duration, status) | stats by (request.host) quantile(0.9, duration) as p90, count() as requests`.
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
| speed | librespeed:8080 | none (a LAN test) |
| obsidian · karakeep · paperless | obsidian:5984 · karakeep:3000 · paperless:8000 | own |
| calibre · sillytavern · marinara | calibre:8080 (`door-calibre`) · sillytavern:8000 · marinara:7860 (`dmz`) | forward (`import authelia`, admins) |
| aiometadata · aiostreams | aiometadata:3232 · aiostreams:3000 (`dmz`) | oidc |

**Gotchas**
- On `edge` it answers `login`, `aiometadata` and `aiostreams` by name (network aliases), for the
  containers that call them from inside (the OIDC issuer, one addon calling another). Through
  Technitium those names are .35, which the host, and so any container on `edge`, can't reach: a
  macvlan never talks to its parent. An app on `edge` that calls another app's name joins this list;
  one on the macvlan reaches .35 directly.
- Public requests come from cloudflared (10.10.100.33) over the macvlan. Caddy trusts only that IP
  for `Cf-Connecting-Ip`, so its logs and the upstreams see the visitor's address.
- `gw_priority` puts the default route on `dmz`. Without it, replies to clients could leave via
  Docker's bridge and be NATed to the host's IP.
- HTTP/3 stays off (`protocols h1 h2`): Obsidian LiveSync's clients misbehave over it.
