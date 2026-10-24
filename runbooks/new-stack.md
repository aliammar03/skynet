# New stack on a Docker host: one PR

Every host with `modules/docker-host.nix` runs doco-cd. It deploys each folder in `stacks/<target>/`
that has a `compose.yaml` (`.doco-cd.<target>.yml`, depth 1) within about a minute of the merge.
**One PR holds everything:** the stack folder (sections 1, 2, 5 and 6), its route and DNS record (3)
and its Gatus row (4). Ali adds his secret values on the branch before merging. Removing the folder
(another PR) removes the stack.

## Values per Docker host

| | docker-admin |
|---|---|
| doco-cd target · stack folder | `admin` · `stacks/admin/` |
| Door (Caddy) · IP | `caddy-admin` · 10.10.60.60 |
| Door sites · pinned upstream certs | `stacks/admin/caddy-admin/conf/sites/` · `stacks/admin/caddy-admin/certs/` (`/etc/caddy-certs/`) |
| Host (agent logs: `ssh skynet@<ip>`) | 10.10.50.40 |
| doco-cd MCP server | `doco-admin` |

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
  macvlan, plus an app that a firewall rule must name (`skynetv2.md` → Conventions → Networks).
  Either way, with a fixed `ipv4_address` and `gw_priority: 1`.

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
  reachable without a login.
- DNS: `<name>` A → the door's IP, as a line in `dns/aliammar.net.zone` in the same PR. Until P2's
  servers are live, Ali adds it in the Technitium-network UI (http://10.10.70.50:5380) instead.
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

## 7. Check before the PR (agent)

- `nix run nixpkgs#docker-compose -- -f stacks/<target>/<name>/compose.yaml config -q`. Run it in a
  temp copy with an empty `secret.sops.env` if the real one isn't there yet.
- A site change: adapt a temp copy of the door's config, then list the site hosts it ends up with.
  `adapt` exits 0 even when an unclosed brace swallows the sites after it, so compare the list with
  the files in `sites/` (one host each):
  ```sh
  door=stacks/<target>/<door>; d=$(mktemp -d); cp -r "$door/conf" "$d/"
  sed -i "s#/etc/caddy-certs#$PWD/$door/certs#g; s#/etc/caddy#$d/conf#g; /acme_dns/d" "$d"/conf/Caddyfile "$d"/conf/sites/*.conf
  nix run nixpkgs#caddy -- adapt --config "$d/conf/Caddyfile" | nix run nixpkgs#jq -- -c '[.apps.http.servers[].routes[].handle[].routes[]?.match[0].host[0] // empty]'
  ```

## 8. After the merge (agent)

- `ssh skynet@<host ip> 'journalctl CONTAINER_NAME=doco-cd --since -10min -o cat' | grep '"stack":"<name>"'`
  shows a `deploying stack` line and no `deployment failed`. doco-cd logs JSON, one object per line.
- `ssh skynet@<host ip> 'journalctl CONTAINER_NAME=<name> -n 50 -o cat'`
- `#alerts` gets "Deployment completed", the Gatus row turns green, and the host's doco-cd MCP shows
  it (`get_project`).

## Gotchas

- `container_name` is unique on the host.
- Renovate opens a PR when the pinned image has an update. Merging it deploys it.
- Deleting the folder (PR) removes the containers. `/opt/appdata/<name>` stays; deleting data is
  Ali's call.
