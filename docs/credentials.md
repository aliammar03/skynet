# Credentials

Who holds what. Every secret in git is a sops file, encrypted to Ali's age key and the one host
that reads it (`.sops.yaml`); the agent never prints or decrypts one on purpose (`AGENTS.md`, rule
3). Minting a third-party credential is Ali's; the agent generates random ones whole. What Ali keeps
outside the lab: `runbooks/survival-kit.md`.

| Identity | Holds | Scope |
|---|---|---|
| Ali | GitHub owner, the age master key, root on the Proxmox nodes, OPNsense and Unraid, the Discord server, the Google, Cloudflare, Tailscale and healthchecks.io accounts | everything |
| `aliammar-skynet` | classic PAT `public_repo`, `workflow` (`github_token`, `secrets/ops.yaml`) | **Write**: branches, PRs, labels, issues. Can't push `main` (the ruleset), or merge what touches a code owner's file without Ali's review; could merge the rest, but won't (ADR-0013) |
| ops host key | `secrets/ops.yaml`, `secrets/ops.komga.yaml`, `secrets/ops.uchiyomi.yaml` | ops |
| the agent (`skynet` on ops) | root on docker-admin, docker-dmz and both DNS servers (sudo), and on PBS (its SSH key from ops, `hosts/ops/agent.pub`); both doco-cd MCPs' restart and job tools (ADR-0011) | those five; everywhere else diagnose only |
| Discord bot "Skynet" | bot token (`discord_bot_token`, `secrets/ops.yaml`) | `#skynet`; the unattended runs' posts (`skynet-post`, a header file curl reads) |
| Renovate app | the repo's contents and PRs | PRs; it never merges |
| docker-admin host key | `secrets/docker-admin.yaml`, `stacks/admin/**` | that host |
| docker-dmz host key | `secrets/docker-dmz.yaml`, `stacks/dmz/**` | that host |
| technitium-network / technitium-core host keys | `secrets/technitium-<node>.yaml`: Technitium's `admin` password (agent-generated), the webhook; `secrets/technitium-<node>.oidc.yaml`: its login client's secret | that host |
| doco-cd API keys | one per Docker host (`doco_api_secret`); ops holds a copy of each (`doco_<target>_api_key`) | REST and MCP: the diagnose tools, and restart and jobs on both hosts |
| `#alerts` webhook | post only (`discord_alerts_webhook` in every host's file; Gatus's and Alertmanager's `secret.sops.env`) | comin, Apprise, Gatus, Alertmanager, Unraid's notifications; healthchecks.io has its own integration |
| caddy-admin, caddy-apps | a Cloudflare token each, Zone → DNS → Edit on `aliammar.net` | DNS-01 |
| cloudflared | the tunnel's token (`stacks/dmz/cloudflared/secret.sops.env`) | the tunnel `skynet` |
| Tailscale | Ali's account; OPNsense holds the subnet router's node key | routes 10.10.50.0/24, 10.10.60.60, 10.10.70.50–51, 10.10.100.35 |
| Tailscale: ops | `tag:ops` node key in `/var/lib/tailscale`; its first login's auth key in `secrets/ops.yaml` | what the tailnet policy lets `tag:ops` reach, over SSH (userspace) |
| rclone | Drive, scope `drive.file`, through Ali's own OAuth client: `rclone.sops.conf` in both backup stacks and `pbs-offsite` (`runbooks/drive-access.md`) | the files rclone created: the backups' and the datastore's copies |
| restic repositories | one password per Docker host (agent-generated) | that host's snapshots |
| PBS root password | VM 2040's `root@pam`, for the UI and the console; agent-generated into `pbs/secret.sops.yaml`, Ali only | that host |
| PBS `pve@pbs` tokens | `core`, `network`: `DatastoreBackup` on their own namespace; their secrets only in each node's storage entry | PVE's backup jobs; they can't remove a backup |
| PVE's PBS encryption keys | one per node (PVE-generated); copies in the survival kit | every guest backup's chunks |
| `skynet@pve` tokens | `read`, PVEAuditor on `/`, one per node (the nodes aren't clustered), held by ops; `metrics`, the same, held by docker-admin's pve-exporter (`stacks/admin/metrics/pve.sops.yml`) | Proxmox, read-only |
| PBS `metrics@pbs` | token `exporter`: audit on the datastore and the host (`stacks/admin/metrics/secret.sops.env`) | pbs-exporter, read-only |
| OPNsense `skynet-read` | API key, held by ops: Diagnostics: ARP Table · Diagnostics: Logs: Firewall: Live View · Diagnostics: PF Table IP addresses · Diagnostics: Routing tables · Firewall: Aliases · Firewall: Rules [new] · Lobby: Dashboard · System: Gateways · Tailscale · System: Deny config write | config writes denied; PF tables and Tailscale's service could change at runtime, and the agent leaves them to Ali |
| OPNsense's exporter user | API key (`stacks/admin/exporters/secret.sops.env`, Ali) | the pages its collectors read; config writes denied |
| Omada's viewer `exporter` | user and password (`stacks/admin/omada-exporter/secret.sops.env`, Ali) | the controller, read only |
| Authelia's OIDC clients | admin's `grafana`, `technitium-network`, `technitium-core`; the apps' `aiostreams`, `aiometadata`, `komga`, `uchiyomi`: secrets agent-generated into each app's `oidc.sops.*` (Technitium's in `secrets/`), digests in each Authelia's `oidc-clients.yml` | each app's login |
| the agent's Komga and Uchiyomi admins | passwords in `secrets/ops.komga.yaml` and `secrets/ops.uchiyomi.yaml` (agent-generated; Ali and ops) | those two apps, through their APIs (ADR-0016) |
| Komf's Komga account `komf@aliammar.net` | password in `stacks/dmz/komga/komf.sops.env` (Ali) | Komga's metadata, as an administrator; komga-wiki uses it too |
| uchiyomi-scan | Ali's Uchiyomi API token, read + write (`stacks/dmz/uchiyomi/scan.sops.env`) | Uchiyomi's library scans |
| the comics bot (Discord; its own, not Skynet's) | bot token, `stacks/dmz/comics-agent/secret.sops.env` (Ali) | `#comics`, Ali alone; `comics-tools` reads Ali's ✅ with it |
| `comics-tools`' Komga API key and Uchiyomi API token | made by Ali under his accounts, `stacks/dmz/comics-agent/tools.sops.env` | Komga's scans; Uchiyomi read + write + admin |
| the comics agent's Codex login | Ali's ChatGPT subscription (device code), in `/opt/appdata/comics-agent/home` | its model (ADR-0017) |
| the arena's lanes | Claude Code's token (`CLAUDE_CODE_OAUTH_TOKEN`, `stacks/dmz/arena/secret.sops.env`, Ali) and Codex's login (device code, `/opt/appdata/arena/codex`) | Ali's Claude and ChatGPT plans, headless (ADR-0018) |

## Planned

Not made yet; each comes with its step in `docs/plans/autonomy.md`.

| Identity | Would hold | Scope |
|---|---|---|
| `skynet@pve!operate` | VM.PowerMgmt on pool `skynet`, one per node, held by ops (Ali mints) | power only: the window's kernel reboots |
| `skynet@pve!provision` | create, change and restore VMs in pool `skynet`, their ISOs on `local` and disks on `local-lvm` (Ali mints) | OpenTofu's plans and applies |
| OPNsense `skynet-alias` | API key: Firewall: Aliases, with config writes (Ali mints) | the alias sync, for aliases merged in `hosts/opnsense/` |
| `secrets/shared/` | a generated value two hosts both read, encrypted for both | those two hosts |
