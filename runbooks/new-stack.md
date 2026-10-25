# New stack on a Docker host: one PR

Every host with `modules/docker-host.nix` runs doco-cd. It deploys each folder in `stacks/<target>/`
that has a `compose.yaml` (`.doco-cd.<target>.yml`, depth 1) within about a minute of the merge.
**One PR holds everything:** the stack folder (sections 1, 2, 5 and 6), its route and DNS record (3)
and its Gatus row (4). Ali adds his secret values on the branch before merging. Removing the folder
(another PR) removes the stack.

## Values per Docker host

| | docker-admin | docker-dmz |
|---|---|---|
| doco-cd target · stack folder | `admin` · `stacks/admin/` | `dmz` · `stacks/dmz/` |
| Door (Caddy) · IP | `caddy-admin` · 10.10.60.60 | `caddy-apps` · 10.10.100.35 |
| Door sites · pinned upstream certs | `stacks/admin/caddy-admin/conf/sites/` · `stacks/admin/caddy-admin/certs/` (`/etc/caddy-certs/`) | `stacks/dmz/caddy-apps/conf/sites/` · none yet |
| Its Authelia (`import authelia`, access rules, OIDC clients) | `stacks/admin/authelia/` · portal `auth` | `stacks/dmz/authelia/` · portal `login` |
| Public (internet) | never | a line in `stacks/dmz/cloudflared/config.yml` |
| Host (agent logs: `ssh skynet@<ip>`) | 10.10.50.40 | 10.10.100.10 |
| doco-cd MCP server | `doco-admin` | `doco-dmz` |

A new Docker host adds its column (`runbooks/new-vm.md` → Docker host). `.sops.yaml` encrypts
`stacks/<target>/**/*.sops.*` for Ali plus that host. Gatus runs on docker-admin and checks every
host (`stacks/admin/gatus/config/admin.yaml`).

## 1. `stacks/<target>/<name>/compose.yaml`

```yaml
services:
  <name>:
    container_name: <name>
    image: <registry>/<image>:<tag>@sha256:<digest>   # nix run nixpkgs#crane -- digest <image>:<tag>
    restart: unless-stopped
    env_file: secret.sops.env        # only if it has secrets
    volumes:
      - ./config.yml:/config/config.yml:ro   # single files, or a subfolder with no *.sops.* files
      - /opt/appdata/<name>:/data            # state; its backup class goes in the README
    networks: [edge]
    healthcheck:
      test: [CMD, wget, -qO-, http://127.0.0.1:<port>/health]
      interval: 30s
      timeout: 5s
      retries: 3
networks:
  edge:
    external: true
```

- **Never mount the stack folder itself.** doco-cd decrypts `secret.sops.env` into it on deploy.
- Use the image's own healthcheck if it has one. An exec-form check needs its tool (`wget`, `curl`)
  in the image. An image with neither can't have one: say so in a comment and cover it with Gatus.
- Write `$$VAR` for a variable the container's shell reads at run time; `$VAR` is compose's.
- No published ports. The door reaches the container by name on `edge`. Only doors join the host's
  macvlan (a fixed `ipv4_address`, and `gw_priority: 1` beside `edge`), plus an app that a firewall
  rule must name, which joins only the macvlan, with a fixed `ipv4_address` (`skynetv2.md` →
  Conventions → Networks).
- An app with no login of its own (auth mode `forward`) stays off `edge`. On the macvlan, it admits
  only the door's address. Otherwise add `door-<name>` to the host's `skynet.docker.doorNetworks`
  and join it from the app and the door. doco-cd can't deploy a stack whose network doesn't exist
  yet, so merge the host change first (on docker-dmz the agent may instead create it by hand with
  the same `docker network create --internal`, D11).

## 2. Secrets: `stacks/<target>/<name>/secret.sops.env`

A changed value recreates the container on the next deploy. Order matters:
1. Random values first (agent), all in one command. It can only create the file whole, never add
   to it, and the values are never shown:
   `python3 -c 'import secrets; print("MY_SECRET=" + secrets.token_hex(32))' | sops encrypt --filename-override stacks/<target>/<name>/secret.sops.env --input-type dotenv --output-type dotenv /dev/stdin > stacks/<target>/<name>/secret.sops.env`
2. Then Ali's values, on the PR's branch:
   `nix shell nixpkgs#sops -c sops stacks/<target>/<name>/secret.sops.env`, commit, push.

## 3. Route (if it has a UI): a site file in the door's sites folder, `<name>.conf`

```
@<name> host <name>.aliammar.net
handle @<name> {
	import authelia
	reverse_proxy <name>:<port>
}
```

- The door reloads it in place. A new pinned cert restarts the door instead.
- Leave out `import authelia` (the door's forward-auth snippet) only for something that must be
  reachable without a login. With it, the app's access rule goes in that door's Authelia
  (`configuration.yml`, above its catch-all deny on docker-dmz).
- Public (docker-dmz only): its ingress line in `stacks/dmz/cloudflared/config.yml`, before the 404,
  with `originServerName: <name>.aliammar.net`. Check it with
  `nix run nixpkgs#cloudflared -- tunnel --config stacks/dmz/cloudflared/config.yml ingress validate`.
- DNS: `<name>` A → the door's IP, as a line in `dns/aliammar.net.zone` in the same PR.
- docker-dmz: if another container there calls the app by its name (an OIDC issuer, an addon), add
  the name to caddy-apps' `edge` aliases. The host can't reach its own macvlan IPs, so Technitium's
  .35 fails from `edge`. A container on the macvlan reaches .35 directly.
- An upstream with a self-signed cert: pin it in the door's certs folder and use
  `tls_trust_pool file /etc/caddy-certs/<name>.pem` (see caddy-admin's `sites/pbs.conf`).

## 4. Monitoring: a row in `stacks/admin/gatus/config/admin.yaml`

- A stack on docker-admin: by container name, since Gatus shares its `edge`
  (`{ <<: *service, name: <name>, url: tcp://<name>:<port> }`, or HTTP on its health URL).
- A stack on another host: through its door, `https://<name>.aliammar.net`, expecting `302` behind
  Authelia. That resolves through Technitium to the door's IP and crosses OPNsense, so docker-admin
  needs a rule to that door on :443. Rule 235 covers the doors in `ROLE_ADMIN_TARGETS`.

## 5. A scheduled job instead of a service

Labels `cd.doco.job.enabled: "true"`, `cd.doco.job.schedule: "@every 5m"` and
`cd.doco.job.notify_on: failure`. No `restart` and no healthcheck, because doco-cd starts it on
schedule. Add `.doco-cd.yml` with `reconciliation: false` in the folder: otherwise the stopped
container counts as missing and is redeployed, with an `#alerts` post, every poll. See
`stacks/admin/heartbeat/`.

## 6. `README.md`

Purpose · URL · auth mode · data paths + backup class · secret key *names* · upstream link · gotchas.

The backup class takes effect in the host's backup stack (`stacks/<target>/backup/`, same PR):
- `data`: nothing to do. The nightly backup copies a snapshot of `/opt/appdata`, every file at one
  instant, so a database is caught as after a power cut, which it restarts from;
- `cache`: the path joins `excludes.txt`. Everything else in `/opt/appdata` is backed up.

## 7. Check before the PR (agent)

- `nix run nixpkgs#docker-compose -- -f stacks/<target>/<name>/compose.yaml config -q`. Run it in a
  temp copy with an empty `secret.sops.env` if the real one isn't there yet.
- A site change: adapt a temp copy of the door's config, then list the site hosts it ends up with.
  `adapt` exits 0 even when an unclosed brace swallows the sites after it, so compare the list with
  the files in `sites/` (one host each):
  ```sh
  door=stacks/<target>/<door>; d=$(mktemp -d); cp -r "$door/conf" "$d/"
  sed -i "s#/etc/caddy-certs#$PWD/$door/certs#g; s#/etc/caddy#$d/conf#g; /^\ttls {/,/^\t}/d" "$d"/conf/Caddyfile "$d"/conf/sites/*.conf
  nix run nixpkgs#caddy -- adapt --config "$d/conf/Caddyfile" | nix run nixpkgs#jq -- -c '[.apps.http.servers[].routes[].handle[].routes[]?.match[0].host[0] // empty]'
  ```

## 8. After the merge (agent)

- The host's doco-cd MCP shows the deploy (`list_deployment_runs`, `get_project`), and `#alerts`
  gets "Deployment completed". doco-cd logs only warnings and errors (`LOG_LEVEL=warn`, JSON):
  `ssh skynet@<host ip> 'journalctl CONTAINER_NAME=doco-cd --since -10min -o cat'` shows no
  `deployment failed`.
- `ssh skynet@<host ip> 'journalctl CONTAINER_NAME=<name> -n 50 -o cat'`
- The Gatus row turns green.

## Gotchas

- `container_name` is unique on the host.
- Renovate opens a PR when the pinned image has an update. Merging it deploys it.
- Deleting the folder (PR) removes the containers. `/opt/appdata/<name>` stays; deleting data is
  Ali's call.
