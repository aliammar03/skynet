# Retire a stack or a machine: one PR

**Untested:** this is written from how doco-cd and the hosts are configured, and nothing has been
retired this way yet. The PR that first uses it fixes what turns out different.

**Agent** steps run on ops as `skynet`; **Ali** steps are his. Destroying a guest or its data is
always Ali's (`AGENTS.md`, rule 5).

## A stack

1. **Agent**, a PR on `<name>/retire`:
   - `stacks/<target>/<name>/` deleted. doco-cd discovers stacks by folder with `delete: true`
     (`.doco-cd.<target>.yml`), so after the merge it takes the stack's containers down. It keeps
     volumes (`remove_volumes: false`), and the stack's data is bind mounts under
     `/opt/appdata/<name>`, which nothing removes.
   - What points at it, found with `git grep -n <name>`:
     - its site file in the door, `conf/sites/<name>.conf`, and its line in `dns/aliammar.net.zone`;
     - its Gatus rows (`stacks/admin/gatus/config/admin.yaml`);
     - public: its line in `stacks/dmz/cloudflared/config.yml`;
     - `forward`: its access rule in the door's Authelia `configuration.yml`; `oidc`: its client in
       `oidc-clients.yml`;
     - its `door-<name>` in `skynet.docker.doorNetworks` and its `systemd.tmpfiles` rules
       (`hosts/<host>/default.nix`);
     - its cache paths in `stacks/<target>/backup/excludes.txt`;
     - rules, alerts or Renovate entries that name it;
     - `docs/lab.md` and `docs/credentials.md`, where they name it.
2. **After the merge** (agent): the host's doco-cd MCP no longer lists it (`list_projects`), and
   `ssh skynet@<host ip> sudo docker ps -a --filter label=com.docker.compose.project=<name>` lists
   nothing. Its door network stays, since the host's config only ever creates them:
   `ssh skynet@<host ip> sudo docker network rm door-<name>`.
3. **Ali**, once he's sure nothing is wanted from it:
   - its data: `ssh -t aliammar@<host ip> sudo rm -r /opt/appdata/<name>`. Its copies age out by
     themselves: the local snapshots within 7 days, Drive's restic snapshots with their retention;
   - what only he holds: its healthchecks.io check, an OPNsense alias or rule naming its address
     (an app on the macvlan), a third-party account or token of its own.

## A machine

A Docker host's stacks go first, each as above, or move to the other host.

1. **Agent**, a PR on `<name>/retire`:
   - `hosts/<name>/` deleted, its secrets with it.
   - What points at it, found with `git grep -n <name>` and its address:
     - `flake.nix`: `nixosConfigurations.<name>` and `installer-<name>`;
     - `.sops.yaml`: its key and its rule; `modules/agent.nix`: its `knownHosts` pin;
       `modules/base.nix`: its entry in `agentRoot`;
     - `stacks/admin/metrics/scrape.yaml`: its targets; `hosts/docker-admin/default.nix`: its
       address among the log shippers; its Gatus rows and DNS records;
     - a Docker host: `.doco-cd.<target>.yml`, its MCP server in `.mcp.json`, its
       `doco_<target>_api_key` in `hosts/ops/secret.sops.yaml` (Ali removes the key:
       `nix shell nixpkgs#sops -c sops unset hosts/ops/secret.sops.yaml '["doco_<target>_api_key"]'`),
       and its column in `runbooks/new-stack.md`. Its entries in `.claude/settings.json` are Ali's,
       as a `jq` command in the PR;
     - `docs/lab.md`'s row and `docs/credentials.md`'s rows.
2. **After the merge** (agent): every other host still builds and deploys (comin's metrics, each
   host's journal). `LogsNotArriving` fires for its name until it has been silent for a week
   (`stacks/admin/logs/README.md` → Gotchas); that silence is Ali's, below.
3. **Ali:**
   - Alertmanager (https://alerts.aliammar.net) → New Silence: `alertname="LogsNotArriving"`,
     `instance="<name>"`, 7 days, comment `retired <name>`;
   - OPNsense: its `HOST_` alias out of every role alias, then deleted; the PR names each;
   - the guest, on its node, after a last look:
     ```sh
     qm stop <vmid>
     qm destroy <vmid>
     ```
     Its PBS backups stay until PBS's prune ages them out; removing them sooner is PBS's UI →
     Datastore `skynet` → Content → the guest's group → Remove;
   - its healthchecks.io checks, and its Tailscale node if it had one.
