# New stack on docker-admin: one PR

**One PR holds everything:** the stack folder (sections 1–2 and 5–6), its route and DNS record (3)
and its Gatus row (4). Ali adds his secret values on the branch before merging. doco-cd deploys
every folder in `stacks/admin/` that has a `compose.yaml` (`.doco-cd.admin.yml`, depth 1) within
about a minute of the merge. Removing the folder (another PR) removes the stack.

## 1. `stacks/admin/<name>/compose.yaml`

```yaml
services:
  <name>:
    container_name: <name>
    image: <registry>/<image>:<tag>@sha256:<digest>   # nix run nixpkgs#crane -- digest <image>:<tag>
    restart: unless-stopped
    env_file: secret.sops.env        # only if it has secrets
    volumes:
      - ./config.yml:/config/config.yml:ro   # files from the folder: single files or a subfolder
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
- Use the image's own healthcheck if it has one. An image with no shell can't run one: say so in a
  comment and cover it with Gatus.
- Write `$$VAR` for a variable the container's shell reads at run time; `$VAR` is compose's.
- No published ports. The door and Gatus reach the container by name on `edge`. Only doors join a
  macvlan, and always with a fixed `ipv4_address`.

## 2. Secrets: `secret.sops.env`

`.sops.yaml` encrypts `stacks/admin/**/*.sops.*` for Ali and docker-admin. A changed value
recreates the container on the next deploy.
- Ali's values, on the PR's branch before the merge:
  `nix shell nixpkgs#sops -c sops stacks/admin/<name>/secret.sops.env`, then commit and push.
- Random values (agent), never shown:
  `python3 -c 'import secrets; print("MY_SECRET=" + secrets.token_hex(32))' | sops encrypt --filename-override stacks/admin/<name>/secret.sops.env --input-type dotenv --output-type dotenv /dev/stdin > stacks/admin/<name>/secret.sops.env`

## 3. Route (if it has a UI): `stacks/admin/caddy-admin/conf/sites/<name>.conf`

```
@<name> host <name>.aliammar.net
handle @<name> {
	import authelia
	reverse_proxy <name>:<port>
}
```

- Caddy reloads it in place. A cert in `caddy-admin/certs/` restarts the container instead.
- Leave out `import authelia` only for something that must be reachable without a login.
- DNS: `<name>` A → 10.10.60.60, as a line in `dns/aliammar.net.zone` in the same PR. Until P2's
  servers are live, Ali adds it in the Technitium-network UI (http://10.10.70.50:5380) instead.
- An upstream with a self-signed cert: pin it as `stacks/admin/caddy-admin/certs/<name>.pem` and
  use `tls_trust_pool file /etc/caddy-certs/<name>.pem` (see `sites/pbs.conf`).

## 4. Monitoring

Add a row to `stacks/admin/gatus/config/admin.yaml`. Gatus is on `edge`, so for example:
`{ <<: *service, name: <name>, url: tcp://<name>:<port> }`, or an HTTP check on its health URL.

## 5. A scheduled job instead of a service

Labels `cd.doco.job.enabled: "true"`, `cd.doco.job.schedule: "@every 5m"` and
`cd.doco.job.notify_on: failure`. No `restart` and no healthcheck, because doco-cd starts it on
schedule. Add `.doco-cd.yml` with `reconciliation: false` in the folder: otherwise the stopped
container counts as missing and is redeployed, with an `#alerts` post, every poll. See `heartbeat/`.

## 6. `README.md`

Purpose · URL · auth mode · data paths + backup class · secret key *names* · upstream link · gotchas.

## 7. Check before the PR (agent)

- `nix run nixpkgs#docker-compose -- -f stacks/admin/<name>/compose.yaml config -q`. Run it in a
  temp copy with an empty `secret.sops.env` if the real one isn't there yet.
- A site change: `caddy adapt` on a temp copy of `caddy-admin/conf` with the paths rewritten and the
  `acme_dns` line removed (`nix run nixpkgs#caddy -- adapt --config <copy>/Caddyfile`).

## 8. After the merge (agent)

- `ssh skynet@10.10.50.40 'journalctl CONTAINER_NAME=doco-cd --since -10min -o cat'` shows
  "deploying stack <name>", then "job completed successfully". Errors name the stack.
- `ssh skynet@10.10.50.40 'journalctl CONTAINER_NAME=<name> -n 50 -o cat'`
- `#alerts` gets "Deployment completed"; the Gatus row turns green; `doco-admin` MCP
  `get_project <name>`.

## Gotchas

- `container_name` is unique on the host.
- Renovate opens a PR when the pinned image has an update. Merging it deploys it.
- Deleting the folder (PR) removes the containers. `/opt/appdata/<name>` stays; deleting data is
  Ali's call.
