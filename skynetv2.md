# Skynet v2 — implementation plan

> Self-run homelab where **git is the control panel**, mature tools do the work, and an AI agent
> (Claude Code) diagnoses and fixes within guardrails. Our code is light glue. v1 is archived
> (`aliammar03/skynet-v1`) and is reference only. Times are PKT (Asia/Karachi).

## How to use this file

- **Fresh session:** read `AGENTS.md`, then **Status** below, then the first unfinished phase.
- **Phase marked `outline`:** first flesh it out here into numbered steps, in a PR. Ali merging that
  PR is the approval. Only then execute.
- **Hard checkpoints:** the agent drafts, Ali acts:
  - credential material (minting tokens, typing values into `sops`);
  - destroying anything;
  - changes to OPNsense, the Proxmox hosts, Unraid, or the Cloudflare/Google accounts;
  - every merge.
- **One tracker:** each phase PR updates Status (and Decisions, if one changes). There is no other
  tracker. Docs state current truth, never stories.

## Status

| Phase | Title | State |
|---|---|---|
| P0 | Foundations + new ops VM | done |
| P1 | docker-admin: admin door, identity, status | done (2026-10-22); 7 admin names move to .60 with P2's Technitium |
| P2 | DNS (Technitium only) + remote access | done (2026-10-23); open: OPNsense rules 140/150/115 and CT 731 `onboot` (see P2 exit criteria) |
| P3 | docker-dmz: apps + public path | done (2026-10-24): docker-dmz with v1's data (#48), its doors (#50) and all ten apps (#51–#61); the apps reach one another only through the door (#64); every image current (#67). Family accounts skipped for now; rule 150 can go now that 135 (ex-840) serves Gatus's `public` row |
| P4 | Backups → Google Drive | in progress (2026-10-25): PBS greenfield done (VM 2040, `pbs/`; v1's PBS removed); PBS's datastore nightly to Drive by plain `rclone sync` (`stacks/admin/pbs-offsite/`; PVE already encrypts its chunks); app data nightly to Drive, hot (`stacks/<host>/backup/`): docker-dmz rebuilt onto btrfs and backed up from btrbk snapshots (#81); `skynet-restore` drilled from a snapshot and from Drive; `runbooks/restore.md` (six cases); a guest restored from Drive's copy (2026-10-27). Next: seven green nights (from 10-26 → 27), the survival kit |
| P5 | Observability (agent eyes) | in progress (2026-10-26): VictoriaMetrics and VictoriaLogs on docker-admin (`stacks/admin/{metrics,logs}`, #88); every host's exporters and journal upload (`modules/observability.nix`, PBS's `pbs/etc/`); the job metrics; alerts: two vmalerts and Alertmanager to `#alerts`, its Watchdog to healthchecks.io (#91; both watchdogs, HostDown, TargetDown and DiskFull proven live 10-27); Grafana at `grafana.aliammar.net` (OIDC through admin Authelia; Live and Backups boards of our own, seven upstream) and the agent's MCP servers at `/mcp`; Ali's first Grafana login 10-27. Next: the week's sizing check (11-03) |
| P6 | Agent autonomy | planned (2026-10-26): the leash first (comin's testing branches off, with the plan), then tiered merges with verify and rollback, the incident loop, the rekey workflow, OpenTofu for our VMs and the OPNsense aliases; after P5 |
| P7 | Retire v1 + disaster recovery | outline |

## Target state

```
proxmox-core (12 cpu, 31 GB)                     proxmox-network (8 cpu, 15 GB)
├ ops          VM 9091  10.10.90.91   NixOS      ├ OPNsense     VM 5001          (Ali-managed)
│   Claude Code · Discord · Remote Control       ├ Omada        CT 525           (unchanged)
├ docker-dmz   VM 10010 10.10.100.10  NixOS      ├ technitium-network VM 7050 10.10.70.50 NixOS
│   doco-cd(dmz) · caddy-apps .35 · cloudflared .33 · Authelia (apps) · apps
├ technitium-core VM 7051 10.10.70.51 NixOS      └ docker-admin VM 5040 10.10.50.40 NixOS
├ PBS VM 2040 · Unraid VM 2020 · HAOS VM 3050        doco-cd(admin) · caddy-admin 10.10.60.60
└ athena CT 10030 (own repo, untouched)              Authelia · Gatus · (P5) VictoriaMetrics/Logs · Grafana
```

**Change flow:**
1. The agent pushes a branch and opens a PR.
2. CI runs (free GitHub-hosted runners).
3. Ali merges.
4. **comin** (hosts) and **doco-cd** (stacks) pull `main` within about 60 s.
5. Results post to Discord `#alerts`.

Nothing outside the lab pushes into it.

## Decisions (locked)

| # | Decision | Why |
|---|---|---|
| D1 | Stacks = Docker Compose, deployed by **doco-cd** (polling, SOPS, auto-discovery, reconciliation) | Simplest mature GitOps; keeps compose; Renovate understands it |
| D2 | Hosts = **NixOS** flake, each host kept current by **comin** (pull) | A host rebuilds from git; no central push credential |
| D3 | Repo **public**; lab **pulls**; CI = static checks on free GitHub runners | GitHub Free only offers rulesets and CODEOWNERS on public repos; nothing inbound |
| D4 | **Authelia**, with an auth mode per app: `own` / `oidc` / `forward`. One instance per door: admin (docker-admin, internal only) and apps (docker-dmz, reachable from the internet), each with its own users | Config lives in git; ~50 MB; OIDC + forward-auth + passkeys. The internet-facing login stays in the DMZ with the apps it guards, so nothing in the DMZ reaches the management VLAN and family accounts never exist on the admin side (2026-10-24) |
| D5 | **Technitium** is the only DNS: two equal NixOS VMs (technitium-network .50, technitium-core .51), each loading the zone and its settings from `dns/` in git. Ad-blocking with HaGeZi Pro; forwarding over plain UDP to PTCL + OpenDNS + Google, all three raced; AdGuard retired | One product; records and settings are reviewed in PRs and a rebuilt VM comes back complete. PTCL's resolver answers known names in ~5 ms, OpenDNS is fastest on unknown ones, Google is a second fallback, and all three hand out the in-ISP CDN caches; PTCL's REFUSED for blocked sites falls through to the others (`runbooks/dns-speed-test/`, 2026-10-24) |
| D6 | Two Docker hosts: **docker-dmz** (apps, core node), **docker-admin** (admin, identity, monitoring; network node) | Segmentation; monitoring survives losing the core node |
| D7 | Agent = **Claude Code** on the ops VM; chat via **Discord** (Channels) + the Claude app (Remote Control) | Telegram is blocked; no custom UI to build |
| D8 | All alerts go to Discord `#alerts` (doco-cd via Apprise, Gatus, healthchecks.io, comin hook, Alertmanager) | One place to look |
| D9 | Offsite = **Google Drive** via rclone with Ali's own OAuth client, scope `drive.file`, **published to production** | Drive is what Ali has; "Testing" mode tokens expire every 7 days; `drive.file` lets rclone see only what it created |
| D10 | No OpenTofu. VMs come from versioned `hosts/<h>/proxmox.sh`; internal DNS records live in `dns/aliammar.net.zone`; the Cloudflare wildcard CNAME is set once by hand | Guests change rarely |
| D11 | The agent never merges. It is **root on docker-dmz and on PBS** (VM 2040). On docker-dmz: passwordless sudo, every command in that host's journal, which also gives it that host's Docker socket, host key and secrets. On PBS: root over SSH from ops. It never prints a secret value or decrypts one on purpose. On docker-dmz's doco-cd MCP it may restart and run jobs. Destroying a project or stack, or on PBS removing a backup, namespace or datastore, asks Ali each time. Everywhere else: no sudo, no Docker socket, no private age key. While it installs a host it is root on the installer, which holds the new host key that `--copy-host-keys` keeps (`runbooks/new-vm.md`); it reads only the public half | The apps host is where operate work happens, and it needs hands; PBS is where P4's offsite copy and its drills happen (both Ali's call, 2026-10-24). docker-admin (admin portal, Gatus, admin secrets) and the DNS servers stay diagnose-only, so GitHub and missing credentials still leash the rest. The install window was already root-equivalent (the agent installs the OS), and it buys a one-PR install |
| D13 | `aliammar-skynet` has **Write**. The `main` ruleset requires a PR and check `nix` and blocks force-push/deletion; no review is required (Ali's call, 2026-10-21) | Branches in one repo, no approval clicks. "Never merge" is a **soft wall**: AGENTS.md + Claude Code deny rules |
| D12 | v1 archived; fresh repo; new ops VM built alongside the old one, which is then retired | Clean start without a blind spot |
| D14 | Remote access = **Tailscale**, with `os-tailscale` on OPNsense as the subnet router and split DNS for `aliammar.net`; replaces the WireGuard plan | Nothing inbound to open; it keeps working when docker-admin or a node is down, so it can reach what needs fixing |
| D15 | Backups = **restic** (run by resticprofile in doco-cd `one_off` jobs) copying `/opt/appdata` **hot**: on docker-dmz from a read-only **btrfs snapshot** taken by **btrbk** a moment before. PBS's datastore goes with **rclone** (PVE encrypts its chunks); both to Drive, nightly. PBS is rebuilt greenfield as VM 2040 from Proxmox's automated installer. Restores: `skynet-restore`, from a local snapshot or from Drive, with doco-cd paused | Battle-tested pieces. A snapshot holds every app's files at one instant, which databases restart from as after a power cut: no dumps, no stopped apps, no stop lists. Holding apps stopped through doco-cd (`stop_services`, the first design) relies on no poll redeploying them mid-job, and doco-cd 0.129.1's can (P4 → Prechecks) |

## Rules

1. **Every change is a PR that Ali merges.** The only planned exception is Renovate automerge of app
   digest/patch updates (P6).
2. **The system rebuilds from git.** Only payload (app data) restores from backup.
3. **Secrets are sops+age only.** Each file's recipients are Ali's master key plus the one host that
   needs it. No plaintext in git, chat or logs.
4. **The agent works in four lanes:**
   - **diagnose:** read anything except secrets;
   - **operate:** granted verbs: root on docker-dmz and PBS, docker-dmz's doco-cd MCP restart and
     job tools (D11), and an Alertmanager silence for its own planned work, ending within 4 hours,
     its comment naming the work (P5); the rest in P6;
   - **change:** via PR;
   - **never:** merge, private keys or a Docker socket outside docker-dmz and PBS,
     OPNsense/Unraid/PVE host config, deleting data.
5. **Ali handles credentials.** He mints tokens and types them via `sops`. The agent never prints a
   secret value. As root on docker-dmz it could read that host's, and doesn't.
6. **Mature tools first.** Custom glue stays inside the Glue budget.
7. **Every routed app has a health check**, and every backup job checks in to healthchecks.io.

## Repo layout (end state)

```
skynet/
├ AGENTS.md  CLAUDE.md (@AGENTS.md)  README.md  skynetv2.md
├ flake.nix  flake.lock
├ modules/            base.nix + observability.nix (all hosts) · agent.nix (ops) · docker-host.nix (docker-*)
├ hosts/<host>/       default.nix · net.nix · disk.nix · hardware.nix · vm.nix (P6; proxmox.sh until then) · ssh_host.pub · README.md
├ secrets/<host>.yaml host-level secrets (sops-nix); secrets/shared/ a value two hosts share (P6)
├ dns/                aliammar.net.zone · settings.json (Technitium, P2)
├ pbs/                PBS, VM 2040: vm.nix (P6) · answer.toml · installer.nix · setup.sh · etc/ (P4)
├ pve/                the Proxmox nodes' exporters and log upload: setup.sh · etc/, Ali runs it (P5)
├ unraid/             README.md: Unraid's exporter containers and syslog target, Ali applies (P5)
├ infra/proxmox/      OpenTofu: our VMs, from each host's vm.nix (P6)
├ opnsense/           aliases.yaml, synced to OPNsense (P6)
├ .doco-cd.admin.yml  .doco-cd.dmz.yml
├ stacks/admin/<stack>/      (P1+)
├ stacks/dmz/<app>/          (P3+)
├ runbooks/                  new-vm · new-stack · dns-speed-test (P2); restore (P4); incident · window (P6)
├ .claude/settings.json  .mcp.json  .sops.yaml  renovate.json  .gitignore
└ .github/workflows/check.yml · rekey.yml (P6)  .github/CODEOWNERS
```

## Conventions

### Stack folder `stacks/<host>/<name>/`

| File | When | Content |
|---|---|---|
| `compose.yaml` | always | `container_name: <name>` (not compose's `<project>-<service>-1`); images pinned `tag@sha256:…`; a healthcheck; `restart: unless-stopped`; network `edge` (doors also join their macvlan; exceptions: Networks) |
| `secret.sops.env` | has secrets | dotenv, sops-encrypted for that host only; used via `env_file` |
| `README.md` | always | purpose · URL · auth mode · data paths + backup class · secret key *names* · upstream link · gotchas |

**Routing**
- Each door has **one wildcard site** `*.aliammar.net`. It imports the app snippets and ends with a
  catch-all `404`.
- The wildcard cert comes via Cloudflare DNS-01, so individual names never appear in certificate
  transparency logs.
- A routed app's site file lives in its door: `conf/sites/<name>.conf` (`@x host x.aliammar.net` +
  `handle @x { [import authelia] reverse_proxy <container>:<port> }`); the door reloads it in place.
- Every app gets a row in Gatus's `config/admin.yaml` (Gatus runs on docker-admin and checks every
  host). Route, row and stack land in one PR (`runbooks/new-stack.md`).
- No container mounts a stack folder itself, because doco-cd writes decrypted secrets into it.
  Mount single files, or subfolders without `*.sops.*` files.

**Auth modes**
- **`own`** (default): a plain proxy; the app has its own login.
- **`oidc`:** the client goes in its door's Authelia: `stacks/<host>/authelia/oidc-clients.yml`
  (the apps' clients in `stacks/dmz/`). That single file holds the whole list, because Authelia
  replaces a repeated key rather than appending to it. The client secret's digest goes there, and the
  plaintext in the app's own `oidc.sops.env`, which the agent generates whole and the compose file
  lists after `secret.sops.env`, so it wins. The provider's keys are in that Authelia's
  `oidc.sops.yml`.
- **`forward`:** add `import authelia` to the app's site file. Each door's snippet asks its own
  Authelia, and the app's access rule goes in that Authelia's `configuration.yml`.

**Data**
- Everything that persists is a bind mount at `/opt/appdata/<stack>/<role>`, databases included
  (their images fix file ownership at start). A host's state is then one folder to back up or move.
  No named volumes.
- Docker creates a missing folder as root and copies none of the image's files into it, as it would
  into a new named volume. An image that runs as a fixed non-root user and doesn't fix its own
  folder gets that folder from the host config (`systemd.tmpfiles`, with its owner), in the stack's
  PR.
- The README gives each path a backup class: data, or cache (rebuilds itself; not backed up).
- Backups (P4) copy `/opt/appdata` hot. docker-dmz's comes from a read-only btrfs snapshot taken a
  moment before: every file at one instant, as after a power cut, which the apps' databases restart
  from. docker-admin's is copied directly (one small SQLite file). Databases need no dumps, nothing
  stops, and a restore is the files put back.

**Networks**
- Shared networks are created by the host's Nix config, not by stacks:
  - `edge`: a bridge shared by apps and doors;
  - a macvlan for the doors (`dmz`, `adm60`);
  - `door-<app>`: an internal bridge for a door and one app, alone (`skynet.docker.doorNetworks`).
- A stack with helpers (a browser, a database, a search engine) gives them a network of its own in
  its compose file (`backend`), so nothing outside the stack reaches them. Only the app joins `edge`.
- Apps get no LAN IP. Doors reach them by container name.
- The exception is an app that a firewall rule must name (its own egress, e.g. usenet). It joins
  only the macvlan, with a fixed IP, so its traffic leaves with that IP. Its door is on the macvlan
  too and reaches it there; no app on `edge` can.
- Every app on `edge` reaches every other. So an app with no login of its own (auth mode `forward`)
  stays off it, and only its door reaches it:
  - on the macvlan (a firewall rule names it), it admits only its door's address;
  - otherwise it joins `door-<app>`, plus a network of its own if it needs the internet.

### Hosts and git

- **Addressing:** VMID = VLAN + two-digit last octet. Static IPs via networkd. NICs are renamed by
  MAC (`lan`, `adm60`, `dmz`).
- **`hosts/<h>/proxmox.sh`** is the exact `qm create` used. It's re-runnable documentation, not
  automation.
- **Age identity:** each host's age key is derived from its SSH host key (`ssh-to-age`). sops-nix
  uses it, and on Docker hosts doco-cd does too.
- **Agent git flow:** the agent pushes branch `p<N>/<slug>` to `origin` and opens a PR. The ruleset blocks
  pushes to `main`; "never merge" is the soft wall (D13). One PR = one reviewable change, CI green first.

## Credentials ledger

| Identity | Holds | Scope | Phase |
|---|---|---|---|
| Ali | GitHub owner, age master key, SSH CA, Proxmox/OPNsense/Unraid root, Discord owner, Google + Cloudflare accounts | everything | — |
| aliammar-skynet | classic PAT `public_repo`, `workflow` | **Write**: branches, PRs, labels. Can't push `main` (ruleset); could merge, but won't (soft wall, D13) | P0 |
| ops host key | decrypts `secrets/ops.yaml` | ops | P0 |
| agent (`skynet`) | root on docker-dmz (sudo) and PBS (SSH key from ops), D11; doco-dmz MCP restart/job tools | those two; everywhere else diagnose-only | P3 / P4 |
| Discord bot | bot token | `#skynet` chat | P0 |
| Renovate app | repo contents/PRs | PRs (automerge P6) | P0 |
| docker-admin host key | `secrets/docker-admin.yaml`, `stacks/admin/**` | that host | P1 |
| caddy-admin / caddy-apps | Cloudflare token `Zone.DNS:Edit` on `aliammar.net` | DNS-01 | P1 / P3 |
| doco-cd API keys | REST/MCP per Docker host | held by ops (diagnose tools only until P6) | P1 / P3 |
| `#alerts` webhook | post only | Gatus, Apprise, comin, healthchecks.io; Alertmanager (P5) | P1 |
| technitium-network / technitium-core host keys | `secrets/technitium-<node>.yaml`: Technitium `admin` password (agent-generated) | that host | P2 |
| Tailscale | Ali's account; OPNsense holds the node key | subnet routes 10.10.50.0/24, 10.10.60.60, 10.10.70.50–51 | P2 |
| docker-dmz host key, tunnel credentials | `stacks/dmz/**`, cloudflared | that host | P3 |
| rclone | Drive, scope `drive.file` (only what rclone created); Ali's own OAuth client | the backup and PBS-offsite jobs | P4 |
| restic repositories | one password per Docker host (agent-generated) | that host's snapshots | P4 |
| PBS `pve@pbs` tokens | `core`, `network`: `DatastoreBackup` on their namespace | PVE's backup jobs | P4 |
| PBS root password | VM 2040's `root@pam` (UI, console); agent-generated into `pbs/secret.sops.yaml`, Ali only | that host | P4 |
| PVE's PBS encryption keys | one per node (PVE-generated); copies in the survival kit | every backup's chunks | P4 |
| `skynet@pve` tokens | `read` = PVEAuditor on `/`, one per node (the nodes aren't clustered); `metrics` = the same, for docker-admin's pve-exporter; `operate` = VM.PowerMgmt on pool `skynet`; `provision` = create, change and restore VMs in pool `skynet`, with their ISOs on `local` and disks on `local-lvm` (OpenTofu) | Proxmox | P1 / P5 / P6 |
| PBS `metrics@pbs` | token `exporter`: audit on the datastore and the host | pbs-exporter, read-only | P5 |
| rekey key | an age key in GitHub environment `rekey`, which only `main`'s workflows can use | recipient of every sops file: re-encrypts once Ali approves a recipient change (P6 → Toil) | P6 |
| OPNsense `skynet-alias` | API key: Firewall: Aliases, with config writes | ops's alias sync, for aliases merged in `opnsense/` | P6 |
| alert webhook | token (agent-generated) | Alertmanager → `skynet-incident` on ops | P6 |
| OPNsense `skynet-read` | API key | Diagnostics: ARP Table · Diagnostics: Logs: Firewall: Live View · Diagnostics: PF Table IP addresses · Diagnostics: Routing tables · Firewall: Aliases · Firewall: Rules [new] · Lobby: Dashboard · System: Gateways · Tailscale · System: Deny config write. Config writes stay denied; PF tables and Tailscale's service could change at runtime, and the agent leaves them to Ali (rule 5) | P1 / P4 |
| Technitium | read-only user | diagnose | P5 / P6 |

---

## P0 — Foundations + new ops VM `[detailed]`

**Goal**
- v1 frozen and archived.
- A fresh public repo with CI and Renovate.
- The new ops VM (NixOS) runs the agent, keeps itself current from `main`, and is reachable via
  Discord and the Claude app.

**Why first:** every later phase is built by the agent from this VM, and needs the repo, keys and
accounts.

### Ali prepares

- **age key:** `age-keygen -o ~/.config/sops/age/keys.txt`. Private key → survival kit (paper +
  password manager). Give the agent the **public** key.
- **SSH key:** the workstation SSH **public** key, for user `aliammar`.
- **Discord:**
  - a private server with channels `#skynet` and `#alerts`;
  - Developer Portal app "Skynet": bot token, **Message Content Intent** on, invited with View
    Channels / Send / Send in Threads / Read History / Attach / Add Reactions;
  - a webhook in `#alerts`.
- **healthchecks.io:** project `skynet` with a Discord integration → `#alerts`. Checks are added per
  phase.
- **ISO on the core node:**
  `wget -P /var/lib/vz/template/iso https://channels.nixos.org/nixos-26.05/latest-nixos-minimal-x86_64-linux.iso`

### Steps

| # | Who | Step |
|---|---|---|
| 1 | agent (on Ali's go) | On VM 9090, list the timers with `systemctl list-timers 'skynet-*'`, then `systemctl disable --now` every `skynet-*` timer **except `skynet-watch`**. watch keeps paging until Gatus replaces it at P1 exit. Running apps, PBS jobs and docker-dmz's own backups are unaffected. |
| 2 | Ali | GitHub: rename `aliammar03/skynet` → `skynet-v1`, then **Archive** it. |
| 3 | agent / Ali | Agent: `git -C ~/skynet remote set-url origin https://github.com/aliammar03/skynet-v1.git`, so v1 never polls the new repo. Ali: repoint or delete other v1 clones (workstation, Obsidian). |
| 4 | Ali | Create `aliammar03/skynet` (public, empty). Create the machine account `aliammar-skynet` with a classic PAT (`public_repo`, `workflow`). Install the Renovate (Mend) app on the new repo. |
| 5 | agent | Build the first commit in `~/skynet-v2` (contents below). `nix flake check` + build `ops` locally. |
| 6 | Ali / agent | Ali adds `aliammar-skynet` as a **Write** collaborator; the agent accepts and pushes `main`. After CI's first run, Ali adds a ruleset on the default branch: require PR, require check `nix`, block force-push and deletion, bypass = Repository admin only (no required review, D13). Actions → workflow permissions read-only, and untick "Allow GitHub Actions to create and approve pull requests". The agent then proves a direct push to `main` is rejected. |
| 7 | Ali | On the core node run `hosts/ops/proxmox.sh`. In the VM console: `sudo -i`; `ip -br link`; `ip addr add 10.10.90.91/24 dev <if>; ip route add default via 10.10.90.1; echo nameserver 10.10.70.51 > /etc/resolv.conf`; `mkdir -p ~/.ssh; curl -fsSL https://raw.githubusercontent.com/aliammar03/skynet/main/hosts/ops/installer.pub > ~/.ssh/authorized_keys` |
| 8 | agent | From 9090 (same VLAN): `nix run github:nix-community/nixos-anywhere -- --flake .#ops --target-host root@10.10.90.91 --generate-hardware-config nixos-generate-config hosts/ops/hardware.nix`. PR with `hardware.nix`. |
| 9 | agent | `ssh-keyscan -t ed25519 10.10.90.91 \| ssh-to-age` → add recipient `ops` to `.sops.yaml` (PR). |
| 10 | Ali | On the workstation, `sops secrets/ops.yaml` with `discord_bot_token` and `github_token` (the aliammar-skynet PAT). Merge. comin applies it and the agent units start. |
| 11 | Ali | `ssh aliammar@10.10.90.91` → `sudo -iu skynet` → `tmux -L skynet attach`. Then: `/login` (Claude subscription), trust `~/skynet`, accept Remote Control, `/plugin install discord@claude-plugins-official`. DM the bot → `/discord:access pair <code>` → `/discord:access policy allowlist`. Run `claude remote-control` once interactively to accept its prompt. |
| 12 | both | Check the exit criteria. |
| 13 | Ali | OPNsense: **add** 10.10.90.91 to alias `HOST_SKYNET_OPS`; .90 stays until P1 exit. |

### First commit

**`flake.nix`**
- Inputs: nixpkgs `nixos-26.05`; nixpkgs-unstable (claude-code only); disko; sops-nix;
  comin (`github:nlewo/comin`).
- Outputs: `nixosConfigurations.ops`; `devShells.default` with sops, age, ssh-to-age,
  nixos-anywhere, gh, jq.

**`modules/base.nix`** (every host)
- flakes, GC + optimise; `time.timeZone = "Asia/Karachi"`; systemd-boot.
- networkd; sshd with keys only and no root login.
- user `aliammar` (wheel, his key, passwordless sudo); qemu-guest-agent; firewall on with 22 open;
  journald kept 2 weeks.
- sops-nix with `sops.age.sshKeyPaths = [ "/etc/ssh/ssh_host_ed25519_key" ]`.
- comin:

```nix
services.comin = {
  enable = true;
  remotes = [{ name = "origin"; url = "https://github.com/aliammar03/skynet.git";
               branches.main.name = "main"; poller.period = 60; }];
  # P1: postDeploymentCommand posts host / status / commit to #alerts
};
```

**`hosts/ops/`**
- `default.nix`: hostname `ops`; 10.10.90.91/24, gateway .1, DNS 10.10.70.51 / .50.
- `disk.nix`: disko, GPT, 512 MB ESP + ext4 `/`.
- `proxmox.sh`:

```sh
qm create 9091 --name ops --machine q35 --bios ovmf --ostype l26 --cpu host --cores 4 \
  --memory 8192 --balloon 0 --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:64,ssd=1,discard=on,iothread=1 \
  --net0 virtio,bridge=vmbr0,tag=90 --agent enabled=1 --onboot 1 \
  --ide2 local:iso/latest-nixos-minimal-x86_64-linux.iso,media=cdrom --boot 'order=scsi0;ide2'
qm start 9091
```

**`modules/agent.nix`**
- User `skynet` with no wheel.
- Packages: git gh jq yq ripgrep fd tmux curl sops age ssh-to-age nodejs **bun** (Channels plugins
  need it) python3, plus `claude-code` from unstable.
- A sops template `agent.env` (`DISCORD_BOT_TOKEN`, `GH_TOKEN`) owned by `skynet`.
- A oneshot that clones `~/skynet` (`origin` = aliammar03/skynet) and
  sets git identity to aliammar-skynet.
- Two units:

```nix
systemd.services.skynet-agent = {   # the persistent conversation: Discord + Claude app
  wantedBy = [ "multi-user.target" ]; after = [ "network-online.target" ];
  serviceConfig = {
    User = "skynet"; WorkingDirectory = "/home/skynet/skynet"; Type = "forking"; Restart = "always";
    EnvironmentFile = config.sops.templates."agent.env".path;
    ExecStart = "${pkgs.tmux}/bin/tmux -L skynet new-session -d -s skynet 'claude --remote-control Skynet --channels plugin:discord@claude-plugins-official --permission-mode auto'";
    ExecStop  = "${pkgs.tmux}/bin/tmux -L skynet kill-server";
  };
};
# skynet-spawn: same shape, tmux session "spawn",
#   'claude remote-control --spawn worktree --permission-mode auto' (on-demand app sessions)
```

  Verify that `--remote-control` and `--channels` work together in one session. If they don't,
  split them into two sessions.

**Repo config**
- `.sops.yaml`: rule `secrets/ops\.yaml` → recipients [ali, ops]. Rules for later hosts and stack
  paths are appended per phase.
- `.claude/settings.json`:
  - deny `Bash(gh pr merge:*)`, `Bash(gh repo edit:*)`, `Bash(gh repo delete:*)`,
    `Bash(git push origin:*)`, `Bash(sudo:*)`;
  - allow read-only shell, `git`, `gh pr create|view|list`, `nix flake check`, `nix build`.
- `.mcp.json`: `nixos` (mcp-nixos).
- `AGENTS.md` (one page or less): role · Rules · lanes · branch→PR flow (never merge) · stack folder
  contract · hard checkpoints · "the plan is skynetv2.md".
- `README.md` (human intro) · `skynetv2.md` (this file) · `.github/CODEOWNERS` (`* @aliammar03`).
- `.github/workflows/check.yml`: runs on PR + push to main; `permissions: contents: read`. Job
  `nix`: checkout → `cachix/install-nix-action` → `nix flake check --no-build` (evaluates every host,
  about 30 s; the host builds, and comin keeps the current generation if a build fails).
- `renovate.json`: `config:recommended`; `nix.enabled: true`; `lockFileMaintenance` weekly
  (Monday, Asia/Karachi); dependency dashboard; no automerge.

### Exit criteria

- CI `nix` is green on `main`; the ruleset is active and a direct push to `main` is rejected.
- comin on ops shows `main`'s HEAD deployed. A trivial merged PR is live within ~2 min.
- After rebooting ops, both agent units come back without manual steps.
- The bot answers in `#skynet` from the new VM. The Claude app shows "Skynet" and can spawn a session.
- The agent opens a PR from a branch, CI runs on it, and Ali merges it.
- v1 timers are off except `skynet-watch`. The v1 repo is archived. The survival kit has the new age key.

---

## P1 — docker-admin: admin door, identity, status `[detailed]`

**Goal**
- `https://<name>.aliammar.net` opens every admin UI with a valid wildcard cert, behind an
  Authelia passkey.
- Gatus watches the lab and posts to `#alerts`.
- The doco-cd pattern is proven on the first Docker host.
- Management Caddy CT 635 and the v1 ops VM are retired.

**Why now:** this is the smallest blast radius (admin users only). It builds the docker-host module,
doco-cd, Authelia, Gatus and alerting, which P3 reuses.

### Prechecks (agent, read-only)

Access: `skynet@pve!read` on each node and OPNsense `skynet-read` (ledger), in `secrets/ops.yaml`.

- **IP and VMID:** 10.10.50.40 is unused (ping, OPNsense ARP, Technitium) and VMID 5040 is free.
- **RAM:** the network node has about 5 GB free, so start docker-admin at 4 GB.
- **DNS:** list the A records already pointing at 10.10.60.35 (v1 vanity names) and confirm each
  admin upstream IP/port in the sites table.
- **Firewall:** list the v1 OPNsense rules that use 10.10.60.35 (`HOST_PROXY_ADMIN`). caddy-admin
  joins that alias at 10.10.60.60, so it gets the same rules.

### Host: `hosts/docker-admin/` + `modules/docker-host.nix`

- **`proxmox.sh`:** VM 5040 on server-proxmox-network: 2 cores, 4096 MB, balloon 0, 32 GB
  `local-lvm`.
  - `net0` **untagged** (VLAN 50 is vmbr0's native VLAN on this node): the host IP 10.10.50.40.
  - `net1` tag 60: no IP; it's the macvlan parent.
  - MACs pinned (`BC:24:11:50:40:01` / `:60`), shared with the configs via `hosts/docker-admin/net.nix`.
- **Install (no console):**
  1. agent: `nix build .#installer-docker-admin` on ops. That's a NixOS ISO with the static IP on the
     MAC-matched NIC, sshd on, and only the agent's key (`hosts/ops/agent.pub`) for root.
  2. Ali, from the workstation:
     `scp -3 aliammar@10.10.90.91:<iso path> root@10.10.50.10:/var/lib/vz/template/iso/nixos-installer-docker-admin.iso`,
     then runs `proxmox.sh` on the node.
  3. agent: `hardware.nix` from the running installer
     (`nixos-generate-config --no-filesystems --show-hardware-config`) goes into the host PR, so CI
     evaluates the real host. After merge: `nixos-anywhere --flake .#docker-admin --target-host
     root@10.10.50.40 --no-substitute-on-destination` from `main` (the whole closure goes over the LAN from ops), then recipient `docker-admin` and its secrets as in P0 steps 9–10.
- **networkd:** NICs renamed by MAC.
  - `lan`: 10.10.50.40/24, gateway .1, DNS .51/.50.
  - `adm60`: up, no address.
- **Docker:** `virtualisation.docker` with log-driver `journald`; a weekly image-only prune (`docker
  system prune` would delete the stopped job containers doco-cd schedules by).
- **Networks:** a oneshot creates them idempotently:
  - `edge`: a bridge;
  - `adm60`: a macvlan on parent `adm60`, 10.10.60.0/24, gateway .1.
- **doco-cd's credentials:** a oneshot `doco-cd-credentials` writes `/run/doco-cd/` (0700) before
  doco-cd starts: `age.key` (`ssh-to-age -private-key` of the host key), `api-secret` and
  `apprise-urls` (copies of the sops secrets). doco-cd mounts only that folder, never `/run/secrets`.
- **`virtualisation.oci-containers`** (`modules/docker-host.nix`, option `skynet.docker.docoTarget`):
  digest-pinned; a Renovate regex manager bumps them.
  - **`apprise`**: published on `127.0.0.1:8000` only.
  - **`doco-cd`:** `--network=host`, so the NixOS firewall governs its ports (a published port would
    bypass it), and `--cap-drop=ALL`.
    - mounts: the Docker socket; `/var/lib/doco-cd` at the same path (`DATA_MOUNT_PATH` =
      `DATA_HOST_PATH`), so stacks' relative bind mounts resolve; `/run/doco-cd:ro`;
    - env: `TZ`, `HTTP_PORT=8080`, `SOPS_AGE_KEY_FILE`, `API_SECRET_FILE`, `MCP_ENABLED=true`,
      `APPRISE_API_URL=http://127.0.0.1:8000/notify`, `APPRISE_NOTIFY_URLS_FILE`,
      `APPRISE_NOTIFY_LEVEL=success`, plus the poll config below;
    - :8080 serves the API, `/mcp` and `/v1/health`; the NixOS firewall admits only 10.10.90.91.
      Metrics stay on :9120, closed until P5.

```yaml
POLL_CONFIG: |
  - url: https://github.com/aliammar03/skynet.git
    reference: main
    interval: 60s
    target: admin        # reads .doco-cd.admin.yml
```

- **LAN Nix cache:** ops runs harmonia on 10.10.90.91:5000 (`modules/nix-cache.nix`, priority 30,
  ahead of cache.nixos.org). Other hosts use it once `hosts/ops/cache.pub` is in git. OPNsense:
  `ROLE_NIX_CACHE_CLIENTS` (each NixOS host but ops) → `HOST_SKYNET_OPS` :5000. A new host joins the alias.
- **comin `postDeploymentCommand`** (in `base.nix`): posts a **failed** deploy (host, status, commit,
  error) to `#alerts`; successes stay quiet.
  It's on for any host whose sops file has `discord_alerts_webhook`.
- **`secrets/docker-admin.yaml`:** `doco_api_secret` (agent-generated, random) and
  `discord_alerts_webhook` (the `#alerts` webhook URL). Apprise takes that URL as-is, so one value
  serves Apprise, comin and Gatus.
- **Guard:** `base.nix` asserts that every sops secret a host uses exists in its file, so CI fails
  instead of the switch on the host.

### `.doco-cd.admin.yml`

```yaml
working_dir: stacks/admin
auto_discovery: { enabled: true, depth: 1, delete: true, remove_volumes: false }
reconciliation: { enabled: true, events: [unhealthy, die, oom] }
timeout: 300
```

### Stacks (`stacks/admin/`)

**`caddy-admin`**
- **Container:** image `ghcr.io/caddybuilds/caddy-cloudflare`; on `adm60` (`gw_priority: 1`) and on
  `edge`; `--watch`. At 10.10.60.60, beside v1's 10.10.60.35, so both run until DNS moves.
- **Reload, not recreate:** label `cd.doco.deployment.recreate.ignore: "{bindMounts: [/etc/caddy]}"`,
  so route edits apply without recreating the container.
- **Files:** `conf/` (mounted at `/etc/caddy`, no secrets): `Caddyfile`, `sites/<name>.conf`; `certs/`
  (upstream certs, public) at `/etc/caddy-certs`, outside `recreate.ignore` so a re-pin recreates. Beside it: `secret.sops.env` (`CLOUDFLARE_API_TOKEN`).
- **Caddyfile:**
  - global (no `email`: Let's Encrypt no longer sends expiry mail): `acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}`, `servers { protocols h1 h2 }`;
  - snippet: `(authelia) { forward_auth authelia:9091 { uri /api/authz/forward-auth; copy_headers Remote-User Remote-Groups Remote-Email Remote-Name } }`;
  - site: `*.aliammar.net { import /etc/caddy/sites/*.conf; handle { respond 404 } }`.

**`authelia`**
- **Container:** image `ghcr.io/authelia/authelia`; on `edge` only (the apps get their own in P3);
  data (sqlite, `notification.txt`) in `/opt/appdata/authelia`.
- **Files:** `configuration.yml` (plaintext, no secrets); `secret.sops.env` (`AUTHELIA_SESSION_SECRET`,
  `AUTHELIA_STORAGE_ENCRYPTION_KEY`, `AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET`,
  agent-generated); `users.sops.yml` (Ali: argon2 hash). OIDC clients for the apps go in the apps'
  Authelia (P3).
- **Config:**
  - authz endpoint `forward-auth` (ForwardAuth);
  - `session.cookies: [{domain: aliammar.net, authelia_url: https://auth.aliammar.net}]`;
  - `storage.local` (sqlite); `notifier.filesystem` for now;
  - `webauthn.enable_passkey_login: true` (a passkey is one factor; `two_factor` adds the password);
  - `password_reset.disable: true` (one user; the password changes by PR);
  - access control: `default_policy: deny`, plus `*.aliammar.net → two_factor`, plus a bypass for
    `status.aliammar.net` `^/api/` from 10.10.90.91 (so the agent can read Gatus).

**`gatus`**
- **Container:** image `twinproduction/gatus`; on `edge`; served at `status.aliammar.net` (behind
  Authelia; `^/api/` open to ops). Sqlite history in `/opt/appdata/gatus`. The image is only the
  binary, so no healthcheck: heartbeat pings only while Gatus answers `/health`.
- **Config loading:** `GATUS_CONFIG_PATH=/config` (`./config` mounted). It's a directory, so all
  files are merged: maps merge and `endpoints` lists append.
- **`config/core.yaml`:** sqlite storage; Discord alerting via `${DISCORD_ALERTS_WEBHOOK}`
  (`secret.sops.env`, Ali copies the `#alerts` URL); default alert: 3 failures to fire, 2 successes
  to clear, send on resolve.
- **`config/admin.yaml`** endpoints, every 60 s, one row per thing:
  - `door`: `auth.aliammar.net/api/health` through caddy-admin, expecting `200` and a cert with more
    than 7 days left. That's Caddy, the wildcard cert and Authelia, which every admin site shares.
    caddy-admin has `auth.aliammar.net` as a network alias on `edge`, so the check needs no DNS
    and no hairpin through OPNsense;
  - `service`: a TCP connect to each admin UI (OPNsense rule 235 lets docker-admin through);
  - `dns`: `auth.aliammar.net A` against .50 and .51 must answer 10.10.60.60.
  - `job` (every 5 min, no alert): heartbeat's healthchecks.io badge (`HC_BADGE_URL_ADMIN`) must say
    `up`. A job's container is stopped between runs, so this row is how the page shows it.
  - doco-cd isn't checked here (its API answers only to ops); heartbeat is a doco-cd job, so a
    dead doco-cd pages via healthchecks.io.
- P3's apps get their rows here too.

**`heartbeat`**
- A `curlimages/curl` doco-cd scheduled job (`cd.doco.job.enabled: "true"`, `notify_on: failure`,
  `cd.doco.job.schedule: "@every 5m"`) that pings healthchecks.io.
- It's the dead-man for the host, Docker, the doco-cd scheduler and egress.
- Its `.doco-cd.yml` sets `reconciliation: false`. Every scheduled job needs this: reconciliation
  treats a job's stopped container as missing and redeploys it on every poll.
- healthchecks.io check `docker-admin` (period 5 min, grace 5 min); `HC_PING_URL` in its
  `secret.sops.env`. `.sops.yaml` encrypts `stacks/admin/**/*.sops.*` for ali + docker-admin.

### Admin sites (`sites/*.conf`)

Every site except `auth` has `import authelia`. Confirm every IP and port in prechecks.
If an appliance cert can't be pinned, use `tls_insecure_skip_verify` and note it in the README.

| Name | Upstream | Note |
|---|---|---|
| opnsense | https://10.10.50.1 | `tls_server_name OPNsense.internal` + trust its cert (`tls_trust_pool file`). In OPNsense, System → Settings → Administration → **Alternate Hostnames** must include `opnsense.aliammar.net` and `auth.aliammar.net` (after an Authelia login the first request's Referer is `auth`, which OPNsense otherwise rejects) |
| proxmox-core / proxmox-network | https://10.10.50.11:8006 / .10:8006 | trust each node's `pve-root-ca.pem` |
| pbs | https://10.10.20.40:8007 | trust its self-signed cert |
| technitium-core / technitium-network | http://10.10.70.51:5380 / .50:5380 | CT 751 / CT 750 |
| omada | https://10.10.50.25:8043 | pin its self-signed cert, `tls_server_name Omada` |
| unraid | http://10.10.20.20 | `header_down Location ^http:// https://` (it redirects to absolute http URLs) |
| auth | authelia:9091 | portal (the apps' is `login`, P3) |
| status | gatus:8080 | `import authelia`; API open to ops (Authelia bypass) |

### DNS, firewall, agent wiring

**DNS** (Ali, in the Technitium-network UI http://10.10.70.50:5380, the primary, until P2): at cutover, point every admin name → 10.10.60.60 and add
the missing ones (`auth`, `status`, …).

**Firewall** (agent drafts the exact rules, Ali applies them in OPNsense):
- `HOST_DOCKER_ADMIN` 10.10.50.40 → internet :443 (GitHub, registries, Cloudflare API, Discord,
  healthchecks.io, Nix caches); → Technitium :53; → NTP.
- `HOST_DOCKER_ADMIN` → `ROLE_ADMIN_TARGETS` : `PORT_ADMIN_PROXY` (rule 235, a copy of 230), for
  Gatus.
- `HOST_SKYNET_OPS` → `HOST_DOCKER_ADMIN` :8080 and :22.
- 10.10.60.60 joins `HOST_PROXY_ADMIN` (alias of the v1 Management Caddy rules 210, 230, 830). Cloudflare
  API :443 is covered by 810 (`NET_WEB_EGRESS` includes 10.10.60.0/24), which DNS-01 needs.

**Agent wiring** (diagnose lane only):
- SSH: user `skynet` on every host but ops (`base.nix`). Agent key from ops only, `restrict`, group
  `systemd-journal`, no sudo, no Docker socket. Ops pins each host key (`hosts/<host>/ssh_host.pub`).
- Ali adds `doco_admin_api_key` (the value of docker-admin's `doco_api_secret`) to `secrets/ops.yaml`.
- `.mcp.json` gets `doco-admin`: http `http://10.10.50.40:8080/mcp`. The `x-api-key` header comes
  from `headersHelper` printing a sops-rendered file, so the key is in no environment or config.
- `.claude/settings.json` denies these doco-cd MCP tools until P6: `destroy_project`,
  `remove_stack`, `control_stack`, `control_project`, `trigger_scheduled_job`, `compact_mirrors`.
  Allowed: list/get tools, `get_health` and `trigger_poll`.

### Cutover

Done in a maintenance window. Rollback = stop caddy-admin, start CT 635.

1. Merge every P1 stack except caddy-admin's macvlan IP. Authelia, Gatus and heartbeat should go green.
2. Set OPNsense Alternate Hostnames.
3. Point the admin names → 10.10.60.60 in Technitium. Done for `opnsense`, `auth`, `status`. The
   other seven (`proxmox-core`, `proxmox-network`, `pbs`, `omada`, `technitium-core`,
   `technitium-network`, `unraid`) move with the new Technitium in P2; until then use their IPs.
   CT 635 is shut down with `onboot 0` (2026-10-22), and `HOST_PROXY_ADMIN` holds only 10.10.60.60.
4. Ali enrolls in Authelia:
   - (done with the authelia PR: an argon2 hash in `users.sops.yml` via `sops`);
   - point `auth` → 10.10.60.60 (done) (it was Authentik's, 10.10.100.35);
   - log in and register a passkey (the code is in `/opt/appdata/authelia/notification.txt`);
   - then `import authelia` per site (done).

   Direct IPs remain the break-glass path.
5. Retire v1 monitoring: VM 9090 is shut down with `onboot 0` (2026-10-22), so `skynet-watch` is
   off and Gatus is the monitor. Remove 10.10.90.90 from `HOST_SKYNET_OPS`.

   CT 635 and VM 9090 stay stopped for 14 days, then Ali destroys them (P7).

### Exit criteria

- Every admin name loads with a valid cert behind an Authelia passkey. Direct IPs still work.
- Gatus is all green. A stopped test container alerts in `#alerts`, and so does its recovery.
  Verified 2026-10-22: `docker stop` on Authelia → doco-cd reconciliation restarted it in 3 s and
  posted; rule 235 disabled → Gatus posted 4 DOWN after 3 min and 4 RESOLVED after re-enabling.
- doco-cd deploys and failed comin deploys post to `#alerts`. The healthchecks.io heartbeat is green.
- The agent lists docker-admin projects and runs via MCP, and answers "is X up?" from Gatus.
- CT 635 and VM 9090 are off. Renovate tracks every pinned image (compose + Nix).

---

## P2 — DNS + remote access `[detailed]`

**Goal**
- Two Technitium VMs that rebuild from git: technitium-network (10.10.70.50, network node) and
  technitium-core (10.10.70.51, core node). Every record and setting comes from `dns/`.
- Ads blocked (HaGeZi Pro); lookups forwarded over plain UDP to PTCL + OpenDNS + Google, raced.
- All ten admin names → 10.10.60.60. Clients can't bypass Technitium. AdGuard and the old CTs are off.
- From anywhere, via Tailscale: `*.aliammar.net` resolves (split DNS) and the management network
  answers by IP.

**Why now:** P3's apps and wildcard need a DNS that git controls. Small blast radius: one server at a
time, the other keeps answering, and the old CT comes back with `pct start`.

### Prechecks (agent, read-only)

Done 2026-10-23:
- VMIDs 7050/7051 are free on both nodes; build IPs 10.10.70.52/.53 are unused (ping, OPNsense ARP).
- RAM: the network node has 2.0 GB free with Authentik stopped; the core node 6.8 GB.
- The old CTs sit on `vmbr0` tag 70 on both nodes.
- Public `aliammar.net` (Cloudflare) holds only its NS records, so the internal zone shadows nothing.
- Resolvers, measured from ops over PTCL (Storm is failover only):
  - answers (p50): Cloudflare ~120 ms at first, then 23–26 ms an hour later; OpenDNS 43 ms (Dubai),
    Quad9 45 ms (Dubai), Google 46–60 ms (Doha); DoH costs 1–3 ms over plain UDP once connected;
  - CDN servers handed out: Google and OpenDNS reach Akamai's in-ISP caches (4 ms) and normal
    YouTube/Facebook edges (~44 ms); Quad9 misses the in-ISP caches; Cloudflare sends YouTube video
    to ~260 ms servers;
  - recursion (Unbound from ops) gets the same CDN servers as Google/OpenDNS but is 3–7× slower
    on names not yet cached (new site p50 295 ms vs OpenDNS 44 ms);
  - overnight per-minute log, 00:41–09:00 (498 rounds, no failures), p50 / p90 in ms:

    | | Cached name, UDP | Uncached name, first ask¹ | DoH, first query after a quiet minute |
    |---|---|---|---|
    | OpenDNS + Google, raced | **44 / 148** | **77 / 160** | 172 / 281 |
    | OpenDNS | 46 / 170 | 136 / 261 | 172 / 286 |
    | Google | 56 / 152 | 150 / 253 | 289 / 427 |
    | Quad9 | 45 / 49 | 161 / 280 | 140 / 272 |
    | Cloudflare | 25 / 29 | 115 / 154 | 105 / 373 |
    | Quad9 + Cloudflare, raced | 25 / 29 | 106 / 150 | – |
    | Recursion | – | 237 / 509 | – |

    ¹ The log asked each round's random name over DoH first (on a connection the cached lookup had
    just warmed), then over UDP. The UDP repeat was usually a cache hit, so only the first ask counts.
    A burst test at 10:00 (fresh names per resolver, UDP) agrees: OpenDNS 63, Cloudflare 110, Google
    148, Quad9 155 ms p50. `dnsbench.py` now uses a fresh name per resolver.

    Steady across the night (no evening-peak data yet). DoH loses 100–230 ms whenever its connection
    went idle, because the providers close it within a minute. Technitium would pay that on the first
    lookup after every quiet spell. Plain UDP has no connection to lose, and no interception showed up
    on it. Cloudflare answers cached names fastest, but OpenDNS + Google raced is quicker on uncached
    ones and hands out the better CDN servers (above). So: **plain UDP to OpenDNS + Google, raced**.
    A day run (11:58–17:58, 359 rounds, a fresh name per resolver) confirms it: raced, 44 / 148
    cached and 62 / 152 uncached. Adding Quad9 only trims the cached p90, which Technitium's cache
    hides, and Quad9 then wins 70% of the races, so the in-ISP CDN servers drop from 17% to 4% of
    answers. Quad9 with ECS (9.9.9.11) is slow on uncached names (174 / 500). PTCL's own resolvers
    weren't in these runs; adding them (2026-10-24) changed the pick to PTCL + OpenDNS + Google
    (`runbooks/dns-speed-test/` → Last result).

- The old zone (Ali's export, 2026-10-23) was a **Forwarder** zone (`FWD "this-server"`): it answered
  its own records and resolved everything else publicly. The new servers started that way too, but a
  Forwarder zone also sends a missing *type* to public DNS. AAAA for `proxmox-core` then came back
  NXDOMAIN from Cloudflare. musl (Alpine containers) and systemd-resolved treat that as "the name
  doesn't exist". So `aliammar.net` is a **Primary** zone (2026-10-23), and caddy-admin's DNS-01
  skips its own propagation check (below).
- DHCP already hands out the Technitium IPs.
- Settings are greenfield: nothing is carried over from the old servers.

### Hosts: `hosts/technitium-network/`, `hosts/technitium-core/` + `modules/dns.nix`

- **`proxmox.sh`:** VM 7050 on server-proxmox-network and VM 7051 on server-proxmox-core: 2 cores,
  1024 MB, balloon 0, 16 GB `local-lvm`, `net0` on `vmbr0` **tag 70**, MACs pinned
  `BC:24:11:70:50:01` / `BC:24:11:70:51:01` (each host's `net.nix`).
- **Install:** `runbooks/new-vm.md`, for the pair in one build PR (below), at the **build IPs**
  10.10.70.52 (technitium-network) and .53 (technitium-core), beside the old CTs. The PR carries the
  hardware and host keys read from the running installers, the recipients and the secrets;
  nixos-anywhere's `--copy-host-keys` keeps those keys.
- **Network:** `lan` renamed by MAC. The host resolves via 127.0.0.1, then the other server.
  `services.resolved` is off (its stub would hold :53). A oneshot sends gratuitous ARP once the
  address is up, so OPNsense learns the new MAC immediately when a VM takes over .50/.51.
- **Technitium** (`services.technitium-dns-server`, 15.6 in nixpkgs 26.05):
  - its admin password is set on its very first start only. The VM installs with its secrets (the
    runbook's single PR), so that start already has it. If the credential can't be loaded, the unit
    doesn't start, so it never runs with `admin`/`admin`;
  - ports 53 TCP/UDP and 5380 (web + API) open in the host firewall; OPNsense decides who reaches
    them;
  - first start creates `admin` with the password from sops (`DNS_SERVER_ADMIN_PASSWORD_FILE`,
    passed as a systemd credential because the unit uses `DynamicUser`), and `DNS_SERVER_DOMAIN` =
    the host's name;
  - logs go to the console, so to journald (the agent reads them over SSH).
- **`technitium-sync`** (oneshot, after Technitium; re-runs when `dns/` changes, and at boot):
  1. log in as `admin`;
  2. apply `dns/settings.json` (Set DNS Settings);
  3. create `aliammar.net` as a Primary zone if it's missing (or convert it, e.g. from Forwarder);
  4. import `dns/aliammar.net.zone` with `overwriteZone=true`, so the zone is exactly the file. The
     file is in Technitium's export format, SOA and NS lines included.

  Idempotent. A failure fails the unit, so the deploy fails and comin posts to `#alerts`. Proven
  against Technitium 15.6.2 before the build:
  - the export equals the file apart from the SOA serial;
  - the Forwarder → Primary conversion and a fresh create both end in the file's zone, with AAAA
    answered "no record";
  - a record or setting changed through the API is undone by the next run;
  - a bad zone line, a mistyped settings key or a wrong password fails the run, and the zone stays
    as it was.
- **`secrets/technitium-<node>.yaml`:** `technitium_admin_password` (agent-generated, random, one per host)
  and `discord_alerts_webhook` (Ali copies the `#alerts` URL, so comin posts failures). Ali reads the
  password with sops to open the UI; settings or records changed in the UI are overwritten on the
  next sync.

### `dns/` — records and settings in git

- **`aliammar.net.zone`** (Technitium's export format, TTL 300): SOA and NS (`ns` → .50 and .51),
  and the admin names `opnsense`, `proxmox-core`, `proxmox-network`, `pbs`, `omada`,
  `technitium-core`, `technitium-network`, `unraid`, `auth`, `status` → 10.10.60.60. Left out of the
  old zone: `arcane` and `caddy` (no site behind them; Arcane retires in P3) and the app names →
  10.10.100.35 (their door and the wildcard arrive in P3). No wildcard until P3.
- **`settings.json`:** Technitium's defaults (cache saved across restarts, prefetch, forwarders
  raced, NXDOMAIN for blocked names) plus, for speed:
  - `serveStaleMaxWaitTime` 0: an expired name is answered from cache at once and refreshed in the
    background, so anything seen in the last 3 days (`serveStaleTtl`) answers in ~1 ms;
  - `cacheMaximumEntries` 100 000 (default 10 000);
  - `dnssecValidation` off: no extra key lookups on misses. Google validates upstream, but over
    plain UDP nothing checks an answer on its way here; accepted for speed;
  - `forwarderTimeout` 1000 ms, `forwarderRetries` 2;
  - forwarders `39.39.39.39` (PTCL), `208.67.222.222` (OpenDNS) and `8.8.8.8` (Google), protocol
    UDP, all three raced (`forwarderConcurrency` 3);
  - blocking with HaGeZi Pro
    (`https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/wildcard/pro-onlydomains.txt`,
    HaGeZi's format for Technitium, ~207k domains), refreshed daily;
  - recursion only for 10.10.0.0/16, 100.64.0.0/10 (Tailscale) and loopback;
  - the same two ranges bypass Technitium's per-client rate limit. It's on by default (600
    queries/min per IP), and a Docker host's containers count as one IP;
  - console logging, local time.
- **A change** = edit + PR. Both servers apply it within ~2 min of the merge.
- **`dns/README.md`:** adding a record, checking it (`dig @10.10.70.50 <name>`), and why the UI is
  read-only in practice.

### Gatus (`stacks/admin/gatus/config/admin.yaml`)

The `dns` group has one Gatus **suite** (one row) per server. Each step alerts on its own:
- the UI (:5380);
- `auth` → 10.10.60.60;
- `auth` AAAA NOERROR (a missing type is "no record", not NXDOMAIN);
- `google.com` NOERROR (forwarding works);
- `googlesyndication.com` NXDOMAIN (blocking works: it's on HaGeZi Pro, and the wildcard format
  covers its subdomains; the list holds only `doubleclick.net`'s subdomains, not the domain).

**caddy-admin's DNS-01** (and caddy-apps' in P3):
- The site's `tls` block holds the Cloudflare provider, `propagation_timeout -1` and
  `propagation_delay 60s`.
- Inside the lab, Technitium answers for `aliammar.net` itself, so Caddy can't see the challenge
  record. It waits a minute, and Let's Encrypt checks Cloudflare.
- The current cert first renews around 2026-12-21. Gatus's door row alerts if the cert gets within
  7 days of expiry.

### OPNsense (agent drafts, Ali applies)

While building (ops already reaches every Skynet VLAN on any port, rule 390):
- new host aliases `HOST_TECHNITIUM_NETWORK` = 10.10.70.52 and `HOST_TECHNITIUM_CORE` = 10.10.70.53;
- both nested in `ROLE_DNS_RESOLVERS`, so rule 100 lets clients and Gatus test them and rule 110
  lets them forward;
- both nested in `ROLE_NIX_CACHE_CLIENTS`.

A cutover then only edits that server's `HOST_` alias (→ .50 / .51).

After cutover:
- `ROLE_DNS_RESOLVERS` = the two `HOST_TECHNITIUM_*` aliases only (AdGuard .30/.31 and the old CTs'
  .50/.51 entries out);
- DHCP: check every VLAN lists both .50 and .51 (one of them alone means no failover); OPNsense's
  own DNS servers are .50, .51;
- rule 140 ("block other DNS and DoT") on; rule 150 ("any → approved upstreams :53") disabled, then
  deleted after a quiet week. It lets any client skip Technitium. P3's cloudflared doesn't need it
  (P3 Prechecks);
- rule 110 ("resolvers → any :53") stays: it carries the forwarding;
- rule 115 (the benchmark's temporary ops → any :53) deleted. The last run ended 2026-10-23 17:58,
  so this one needn't wait for the cutover.

### PRs and cutover

- **Build PR:** `modules/dns.nix`, `dns/` (with its README), both hosts (`runbooks/new-vm.md`, as a
  pair) and the Gatus rows for the build IPs. Merge, then install both. They answer at .52/.53 next
  to the old CTs.
- **Cutover PRs, one per server,** so the other keeps answering: `net.nix` → the final IP, that
  server's Gatus rows and its README. The agent's known_hosts entry lists both IPs from the build PR
  on, so it needs no change. Ali moves the server's `HOST_` alias in OPNsense **once the VM answers
  on its final IP**. Moved earlier, the VM (still on its build IP) loses ops's Nix cache, and its
  deploy stalls on timeouts.

1. Both VMs green at the build IPs: every zone name answers right, blocking works, forwarders reach
   out, Gatus rows green.
2. **technitium-core → .51** (done 2026-10-23): Ali `pct shutdown 751 && pct set 751 --onboot 0`,
   then merges technitium-core's cutover PR. Check by name from ops and docker-admin; Gatus green.
   Measured right after: the same as CT 750 on cached names (~0.6 ms), faster on the rest (uncached
   names p50 63 vs 102 ms, new sites 56 vs 167 ms), same CDN servers.
3. **technitium-network → .50:** the same with CT 750.
4. The OPNsense changes above. AdGuard CT 731: `pct shutdown 731 && pct set 731 --onboot 0`
   (730 is already off).
5. CTs 750, 751, 730 and 731 stay stopped for 14 days, then P7 destroys them.

Rollback for either server: stop its VM, `pct start` its CT (same IP). Nothing on the VMs needs a
backup: cache, stats and logs are disposable, and everything else rebuilds from git.

### Tailscale (agent drafts, Ali applies)

1. Ali creates the Tailscale account and an auth key (one-off, pre-approved).
2. OPNsense: install `os-tailscale`. VPN → Tailscale: enable, the auth key, advertise
   `10.10.50.0/24, 10.10.60.60/32, 10.10.70.50/32, 10.10.70.51/32`, don't accept DNS.
3. Tailscale admin: approve the OPNsense node's routes; disable its key expiry.
4. Tailscale admin → DNS: nameservers 10.10.70.50 and .51, each restricted to `aliammar.net` (split
   DNS). MagicDNS on; "override local DNS" off.
5. OPNsense: Interfaces → Assignments → device `tailscale0` (it appears only once Tailscale is
   running) → `TAILSCALE`, enabled, no IP config. Rules on it (sequence 270–272), from alias
   `NET_TAILNET` (100.64.0.0/10): → `HOST_PROXY_ADMIN` :443; → `ROLE_DNS_RESOLVERS` :53; → MGMT net
   (10.10.50.0/24) on `PORT_ADMIN_BREAKGLASS`. Tailscale's "Override DNS servers" belongs to global
   nameservers, so it doesn't apply here (split DNS only).
6. Devices: install Tailscale and sign in (Linux: `tailscale up --accept-routes`).

### Exit criteria

Met on 2026-10-23, apart from the items marked open:
- `dig @10.10.70.50` and `@10.10.70.51`: every admin name → 10.10.60.60, `googlesyndication.com` blocked,
  the internet resolves. Gatus `dns` rows green. ✅
- Both VMs were configured only from git, and a merged record change shows on both within ~2 min. ✅
  (#42 changed the zone; both servers had it within minutes.)
- Every VLAN's DHCP lists both .50 and .51 (Ali); `ROLE_DNS_RESOLVERS` = the two `HOST_TECHNITIUM_*`
  aliases ✅. CTs 730, 731, 750 and 751 are stopped ✅. **Open:**
  - rule 140 on, rule 150 gone, rule 115 deleted;
  - CT 731 `onboot` 0.
- All ten admin names load behind Authelia. ✅ OPNsense's Alternate Hostnames now include
  `auth.aliammar.net` (P1 sites table).
- On mobile data via Tailscale, a phone opens `https://opnsense.aliammar.net` and
  `https://10.10.50.11:8006`. ✅ OPNsense: `TAILSCALE` interface, alias `NET_TAILNET`, rules 270–272.

Deferred:
- Technitium SSO, and the login screen. Authelia stays for now; an Authentik trial comes later
  (P3 → Open).

## P3 — docker-dmz: apps + public path `[detailed]`

**Goal**
- docker-dmz (VM 10010, 10.10.100.10, core node) runs the apps from git, each at its old URL with
  its v1 data.
- Two doors run on it: caddy-apps (10.10.100.35) and cloudflared (.33). The tunnel is new, and its
  routes live in git. The six public names work from the internet.
- The apps without a login of their own (calibre, sillytavern, marinara) sit behind the apps' own
  Authelia on docker-dmz (portal `login.aliammar.net`), from inside and outside. Admin Authelia stays
  internal.
- v1's docker-dmz (VM 10015, with Arcane) and Authentik (CT 837) stay off.

**Why now:** the apps are down (Prechecks). P3 brings them back on a host that rebuilds from git
and fits the node's memory.

### Prechecks (agent, read-only)

Done 2026-10-24:
- **v1 is down:**
  - VM 10015 (8 vCPU, 16 GB, 256 GB, core node) is stopped. Its last task is its start on
    2026-09-16. With no stop task since, it went down from inside or was killed. The likely cause is
    the host's OOM killer: with 10015 running, the node's VMs added up to its 31 GB, and the node
    has 1.3 GB in swap.
  - Authentik CT 837 was stopped on 2026-10-22.
  - Public `aliammar.net` has no app records, so the public path is down too.
- **Room:** VMID 10010 is free on both nodes; 10.10.100.10, .33 and .35 are silent (ping, ARP).
  Core node: 31.2 GB RAM, 16.8 GB used with 10015 off. `local-lvm` has 168 of 348 GB free.
- **The apps** come from v1's archived repo (`compose/`); see the Apps table. Their state is in
  `/opt/docker/appdata/<svc>/<role>`, plus Docker volumes for CouchDB, Meilisearch and Jikan's
  databases. Sizes: Data step 1.
- **Rules that name v1 containers:**
  - aiostreams .65 (usenet, rule 820);
  - marinara .85 and sillytavern .69 (ComfyUI on the workstation, rule 340);
  - cloudflared .33 (rule 800);
  - the door .35 (rules 200 and 430, and 240/245 to Authentik).
- **DNS:** the new Technitium answers cloudflared's SRV lookup
  (`_v2-origintunneld._tcp.argotunnel.com`); the old CTs answered it empty. So cloudflared uses the
  normal resolvers and doesn't need rule 150.

### Host: `hosts/docker-dmz/` (`runbooks/new-vm.md`, Docker host part included)

- **`proxmox.sh`:** VM 10010 on server-proxmox-core:
  - 6 cores, 10240 MB, balloon 0;
  - 128 GB on `local-lvm`: v1's data is 6.5 GB (Data step 1), and aiometadata's poster cache refills
    up to 20 GB;
  - one NIC: `virtio=BC:24:11:00:10:01,bridge=vmbr0,tag=100`.
- **Memory:** with 10 GB here, the node's VMs use 25 of its 31 GB (ops 8, Unraid 4, HAOS 2,
  technitium-core 1). With v1's 16 GB they used all of it. Stacks set memory limits that fit.
- **Network:** NIC `dmz` (VLAN 100) carries the host IP 10.10.100.10/24 (gateway .1, DNS .51/.50).
  It is also the parent of the `dmz` macvlan (10.10.100.0/24). The host can't reach its own macvlan
  IPs, and nothing needs it to.
- **Docker:**
  - `docker-host.nix` with `docoTarget = "dmz"`, and `.doco-cd.dmz.yml`;
  - `stacks/dmz/heartbeat` (healthchecks.io check `docker-dmz`; Gatus row `docker-dmz heartbeat`
    from its badge);
  - MCP `doco-dmz` for the agent;
  - `rsync`, for the data move.

### Apps

| Stack (`stacks/dmz/`) | Name | Auth | Public | State (`/opt/appdata/<stack>/`) | From v1 |
|---|---|---|---|---|---|
| `librespeed` | speed | none (a LAN test) | | `data` | librespeed |
| `obsidian` | obsidian | own (CouchDB) | ✓ | `couchdb` | obsidian-livesync (volume) |
| `karakeep` (+ chrome, meilisearch) | karakeep | own | ✓ | `data`, `meili` | karakeep |
| `paperless` (+ redis) | paperless | own | | `data`, `media`, `consume`, `export` | paperless-ngx |
| `calibre` | calibre | forward | ✓ | `config` | calibre |
| `sillytavern` | sillytavern | forward | | `config`, `data`, `plugins`, `extensions` | silly |
| `marinara` | marinara | forward (its own login off) | | `data` | marinara |
| `jikan` (+ mongo, redis, typesense) | – | – | | `mongo`, `typesense`, `redis` | aiometadata's `jikan_*` |
| `aiometadata` (+ redis) | aiometadata | oidc | ✓ | `data`, `cold-store`, `redis` (`poster-cache` starts empty and refills, capped at 20 GB: `POSTER_CACHE_MAX_SIZE=20g`; v1 had 50g) | aiometadata |
| `aiostreams` | aiostreams | oidc | ✓ | `data` | aiostreams |
| caddy-apps site | homeassistant | own | | | → `http://10.10.30.50`, as in v1 |
| `authelia` | login | (the portal) | ✓ | `data` | new: the apps' Authelia |

- **The names stay.** Clients hold these URLs (LiveSync, Stremio addon links, bookmarks).
- **Jikan** is the self-hosted MyAnimeList API that aiometadata reads, and it becomes its own stack.
  aiometadata reaches `jikan:8080` on `edge`; Jikan's databases sit on an internal network.
- **Image versions:** every image is at its newest release, except the databases an app pins in
  its own compose: Meilisearch v1.41.0 (karakeep), and Mongo 6.0, Redis 6 and Typesense 0.24.1
  (jikan). Renovate keeps within those pins (`renovate.json`).
- **Firewall identity:** aiostreams (.65), marinara (.85) and sillytavern (.69) join only the macvlan,
  with their v1 IPs, so rules 820 and 340 keep naming them. caddy-apps reaches them there.
- **No login, no neighbours** (Conventions → Networks): calibre is on `door-calibre`, with
  caddy-apps alone. sillytavern and marinara admit only caddy-apps' address (`SILLYTAVERN_WHITELIST`;
  `IP_ALLOWLIST`, with marinara's Docker and Tailscale bypasses off).
- **OIDC:** aiostreams and aiometadata used Authentik's OIDC, and family members sign in to them now
  and then. They move to the apps' Authelia's OIDC (`stacks/dmz/authelia/`), set up in the same PR
  as them:
  - the provider: an HMAC secret and a signing key, generated by the agent straight into sops files;
  - one client per app. The agent generates its secret into the app's `oidc.sops.env` and puts the
    secret's digest in `oidc-clients.yml`;
  - family accounts in its `users.sops.yml`, in group `family` (Ali adds the password hashes; none
    yet, skipped for now on 2026-10-24). They
    keep their Authentik usernames, because both apps name users by `preferred_username`. Ali has an
    account there too, in group `admins`;
  - access: the two apps take a password (`one_factor`) from `family` or `admins`. Admin Authelia
    has no family accounts, and its sites stay `two_factor` and Ali only.
- **Secrets:** v1's values carry over, because some of them encrypt data (marinara's
  `ENCRYPTION_KEY`, karakeep's `NEXTAUTH_SECRET`). Ali pipes each v1 file into the new one, so no
  value is ever shown:
  `SOPS_AGE_KEY_FILE=<v1 key> nix shell nixpkgs#sops -c sops -d --input-type dotenv --output-type dotenv <v1>/compose/<svc>/.env.sops | nix shell nixpkgs#sops -c sops encrypt --filename-override stacks/dmz/<stack>/secret.sops.env --input-type dotenv --output-type dotenv /dev/stdin > stacks/dmz/<stack>/secret.sops.env`.
  v1's `.env.git` (the non-secret part) becomes the compose `environment:`.

### Data (Ali, once)

The agent can't log in to 10015 and isn't root on docker-dmz. So Ali moves the data, once, before
the apps deploy:
1. **Before the host PR** (done 2026-10-24):
   1. On the core node: `qm set 10015 --memory 8000 --onboot 0 && qm start 10015`. Docker starts
      every v1 container at boot, and in 2 GB they starve the VM until even SSH stops answering.
      docker-dmz doesn't exist yet, so 8 GB fits.
   2. On the core node, through the guest agent (no SSH needed):
      `qm guest exec 10015 -- systemctl disable --now docker.socket docker.service`. This stops the
      containers and frees their IPs; from then on the VM needs little memory.
   3. `qm guest exec 10015 --timeout 300 -- sh -c 'du -sh /opt/docker/appdata/* /var/lib/docker/volumes/*/_data'`,
      sent to the agent, which sizes the disk from it. To copy: 6.5 GB (calibre 2.4, karakeep 1.8,
      jikan's Mongo 1.0, marinara 0.8; the rest under 0.2 each). Not copied: aiometadata's poster
      cache (8.9 GB; it refills), Arcane, v1's caddy-apps and cloudflared, and the anonymous 4 KB
      volumes.
   4. For the copy, Ali's workstation key (`modules/base.nix`) goes into his user's
      `~/.ssh/authorized_keys` on 10015 (also through `qm guest exec`).
2. **With the install** (done 2026-10-24):
   1. Before the installer boots (`runbooks/new-vm.md` step 2), make room for both VMs:
      `qm shutdown 10015 && qm set 10015 --memory 2048 && qm start 10015` (Docker stays off). With
      10015 at 8 GB, the core node has 8 GB free, less than docker-dmz's 10.
   2. After the install: from a workstation shell with the key in an agent
      (`eval "$(ssh-agent -s)"; ssh-add`), `ssh -A <you>@10.10.100.15` and run the copy in
      `hosts/docker-dmz/README.md` (v1's data). It's one line per path of the table, each
      `sudo --preserve-env=SSH_AUTH_SOCK rsync -aHAX --numeric-ids --mkpath --rsync-path='sudo rsync' <v1 path>/ aliammar@10.10.100.10:/opt/appdata/<stack>/<role>/`.
      - `--preserve-env=SSH_AUTH_SOCK` lets root's ssh use the forwarded key.
      - `--numeric-ids` keeps the owners (CouchDB runs as 5984, Mongo as 999).

      All 21 paths arrived with v1's sizes and owners.
3. `sudo poweroff` (done 2026-10-24). Until P7, 10015 keeps v1's data as it was.

### Doors and auth (one PR, docker-dmz)

- **caddy-apps** (`stacks/dmz/caddy-apps/`, a copy of caddy-admin):
  - on the macvlan at 10.10.100.35 (`gw_priority: 1`), and on `edge`;
  - the same wildcard site and DNS-01 `tls` block; HTTP/3 stays off (Obsidian LiveSync);
  - its `authelia` snippet asks the apps' Authelia, `authelia:9091` on docker-dmz's `edge`;
  - it keeps both Authelias' session cookies (scoped to `.aliammar.net`, so browsers send them to
    every app) from the apps: admin Authelia's is dropped from every request, and the apps' one from
    every name but `login`. Only its forward-auth check gets the apps' session;
  - sites `login` (→ the apps' Authelia) and `homeassistant`. Each app adds its own.
- **The apps' Authelia** (`stacks/dmz/authelia/`, a copy of admin's): on `edge` only, nothing
  published.
  - portal `https://login.aliammar.net`; its own session cookie name (`authelia_apps_session`), so the
    two instances' cookies never overwrite each other;
  - its own `users.sops.yml` (Ali first; the family with the OIDC PR) and secrets (agent-generated);
  - `default_policy: deny`. Each app's PR adds its access rule.
- **Admin Authelia is unchanged:** `auth` stays on caddy-admin (10.10.60.60), nothing is published
  on docker-admin, and the DMZ gets no rule into the management VLAN.
- **cloudflared** (`stacks/dmz/cloudflared/`):
  - only on the macvlan, at .33 (rule 800): it reaches caddy-apps there by name, and no app
    directly;
  - `config.yml`: the tunnel ID, then one line per public name → `https://caddy-apps` (TLS name = the
    public name), then `http_status:404`;
  - `secret.sops.env`: `TUNNEL_TOKEN`, the tunnel's credentials as one token. Not a credentials
    file: doco-cd writes decrypted files root-only, and cloudflared runs as its image's own user.
- **DNS** (`dns/aliammar.net.zone`): `login` and `homeassistant` → 10.10.100.35.
- **Gatus:**
  - `caddy-apps + authelia`: `https://login.aliammar.net/api/health` through Technitium (→ .35,
    rule 235). It expects 200 and a cert with more than 7 days left.
  - `public`: the same URL resolved through 1.1.1.1 (`client.dns-resolver`), so it goes Cloudflare →
    tunnel → cloudflared → caddy-apps → the apps' Authelia.

### Cloudflare (Ali)

1. On the workstation:
   1. `nix shell nixpkgs#cloudflared -c cloudflared tunnel login`, and pick zone `aliammar.net`.
   2. `nix shell nixpkgs#cloudflared -c cloudflared tunnel create skynet`. It prints the tunnel ID
      (not secret; it goes in `config.yml`) and writes `~/.cloudflared/<id>.json`.
2. On the doors branch, the tunnel's token, straight into sops (never shown):
   `nix shell nixpkgs#cloudflared nixpkgs#sops -c sh -c 'set -e; t=$(cloudflared tunnel token skynet); printf "TUNNEL_TOKEN=%s\n" "$t" | sops encrypt --filename-override stacks/dmz/cloudflared/secret.sops.env --input-type dotenv --output-type dotenv /dev/stdin > stacks/dmz/cloudflared/secret.sops.env'`.
3. DNS: `*` CNAME `<id>.cfargotunnel.com`, proxied (D10), while `cert.pem` still exists:
   `nix shell nixpkgs#cloudflared -c cloudflared tunnel route dns skynet '*.aliammar.net'`. A name
   with no ingress line gets 404. Then delete `~/.cloudflared/<id>.json` and `cert.pem`.
4. An API token for caddy-apps (Edit zone DNS, `aliammar.net` only) → `CLOUDFLARE_API_TOKEN` in
   `stacks/dmz/caddy-apps/secret.sops.env`.

The tunnel is new rather than v1's: v1's credentials need v1's key, and P7 revokes them anyway (it
deletes tunnel `b5171e13…`).

### OPNsense (agent drafts, Ali applies)

- **With the host:** `HOST_DOCKER_DMZ` → 10.10.100.10 (it was v1's .15), nested in
  `ROLE_NIX_CACHE_CLIENTS`. From v1, the alias is also in rule 300 (SMB/NFS → Unraid) and in
  `ROLE_ADMIN_TARGETS` (rules 230, 235). docker-dmz needs neither, and both are harmless: the host
  opens only :22, and :8080 to ops.
- **With the doors:**
  - Tailscale: also advertise 10.10.100.35/32 and approve it. Rule 273: `NET_TAILNET` →
    `HOST_PROXY_APPS` `PORT_WEB`, for the app names. Admin names and their logins stay on
    caddy-admin (rule 270);
  - rule 840: `HOST_DOCKER_ADMIN` → 1.1.1.1 :53, for Gatus's `public` row. P2's rule 150 can then go.
- **Unchanged, and still right:** 200 (app clients → .35), 235 (Gatus → doors), 340, 430, 800, 810
  and 820.
- **After the last app:** rules 240/245 (Authentik) disabled. P7 deletes them, along with
  `HOST_AUTHENTIK`, `PORT_AUTHENTIK` and v1's .15 in `ROLE_NFS_CLIENTS` and `ROLE_OPS_SSH_TARGETS`.

### PRs and order

1. Ali: Data step 1 (the sizes). Done.
2. **Host PR** (`runbooks/new-vm.md`): docker-dmz with its heartbeat (Ali adds the healthchecks.io
   check), its MCP and its column in `runbooks/new-stack.md`. 10015 drops to 2 GB before the
   installer boots (Data step 2.1). Then install.
3. Ali: Data step 2.2 (the copy), then powers 10015 off. Done.
4. **Doors PR:** caddy-apps, cloudflared, the apps' Authelia, DNS and Gatus. Ali does Cloudflare,
   OPNsense and his account's password hash.
5. **The apps** (`runbooks/new-stack.md`, plus a tunnel line if public): librespeed, obsidian and
   karakeep one PR each, proving the pattern; then, at Ali's call, the other seven in one PR with
   the apps' OIDC (provider, the two clients; Ali adds the family accounts).

Rollback: revert an app's PR. Until P7, v1 can come back as it was: stop docker-dmz's doors (they
hold .33/.35), give 10015 its memory back, then `sudo systemctl enable --now docker` on it.

### Exit criteria

- Every app answers at its URL from inside, with v1's data: notes sync, bookmarks, documents and the
  Stremio addons. The six public names also answer from a phone on mobile data.
- Gatus is green: the apps door, `public` and every app. docker-dmz's deploys post to `#alerts`, and
  its heartbeat is green.
- From outside, calibre sends a visitor to `login.aliammar.net` and back.
- A family account signs in to aiostreams through the apps' Authelia, and doesn't exist on the admin
  door (skipped for now: no family accounts yet, Ali 2026-10-24). Nothing in the DMZ reaches
  docker-admin.
- Over Tailscale, an app name and an admin name both open.
- 10015 and CT 837 are stopped with `onboot 0` (Arcane went with 10015). P7 destroys them after 14
  days.

**Open:**
- Trial Authentik as the login service (not a P3 step): a custom login screen (CSS, backgrounds),
  forward-auth + OIDC, config as blueprints in git. It would replace Authelia (a D4 change) and needs
  docker-admin resized. Technitium SSO waits for this choice; the two OIDC clients would move with it.

## P4 — Backups → Google Drive `[detailed]`

**Goal**
- Every night, each Docker host's app data (`/opt/appdata`) goes to Google Drive as an encrypted
  restic snapshot. It is copied hot, on docker-dmz from a btrfs snapshot taken a moment before, so
  no app stops.
- PBS is rebuilt greenfield: VM 2040 from Proxmox's installer, its config in git (`pbs/etc/`), with
  none of v1's leftovers.
- Every night, PBS's datastore (every guest's backups, already encrypted by PVE) is mirrored to
  Drive.
- One command restores a stack's data, from a local snapshot or from Drive: `skynet-restore`.
- A failed or missed night posts to `#alerts`, and Gatus shows each job.

**Why now:** PBS already backs up every guest nightly, onto Unraid in the same house: 02:00 on the
network node, 03:30 on the core node, everything but Unraid (VM 2020) and PBS itself (CT 240).
Nothing is offsite, and app data restores only as a whole VM.

### Tools (researched 2026-10-24)

| Need | Choice | Why | Passed over |
|---|---|---|---|
| Backup engine | restic 0.19 | client-side encryption, dedup, snapshots and retention; `restore --delete` puts a folder back exactly; its `rclone:` backend reaches Drive | Kopia (younger), Borg (no Drive), Duplicati (database corruption history), tarball tools such as offen/docker-volume-backup (no dedup: a full upload every night) |
| Runner | resticprofile 0.33, in doco-cd `one_off` jobs; its image ships restic, rclone and curl | one profile file in git holds backup, retention, check and the healthchecks.io pings (`send-before` / `send-after` / `send-after-fail`) | Backrest, autorestic; NixOS `services.restic` (would fit now that nothing stops, but the job already carries the pings, retention and Gatus rows) |
| Point-in-time copy | btrbk 0.32 (NixOS module `services.btrbk`): a read-only btrfs snapshot of docker-dmz's `/opt/appdata` at 04:20, which restic copies at 04:30 | a snapshot holds every file of every app at one instant. SQLite, CouchDB and MongoDB all restart from that state as from a power cut, so there are no dumps and nothing stops. btrbk is the standard btrfs snapshotter, with date-based retention, and its snapshots double as fast local restores | cold copies through doco-cd's `stop_services` (the first design: a poll can redeploy held services mid-job, Prechecks); a dump per database (code and an import step per app); snapper (built for OS rollback, keeps its snapshots inside the data); LVM-thin snapshots (more steps); a plain hot copy (MongoDB's files can't be copied live) |
| Restores | `skynet-restore` (glue): rsync from a local snapshot, or restic 0.19 (nixpkgs-unstable) from Drive, with the backup stack's own sops files through sops-nix | one command for either source. It pauses doco-cd itself, so nothing restarts a stack mid-restore | restores through doco-cd's job (the same mid-job redeploy); httm (it browses file versions, but restores one file at a time) |
| Drive | rclone with Ali's own OAuth client, scope `drive.file` (D9) | rclone sees only the files it created. rclone's shared client stops working during 2026 | a service account (no storage on a personal Drive) |
| PBS offsite | `rclone sync` of the datastore | chunks are immutable files, so each night sends only new ones. PVE already encrypts them client-side; only guest IDs, names, sizes and dates show. Drive keeps deleted files in the trash for 30 days | a second PBS (remote sync); PBS 4's S3 datastores (Drive isn't S3); restic over the datastore (re-deduplicating PBS's chunks); an rclone `crypt` layer (a second key for nothing) |
| PBS itself | a fresh VM from Proxmox's automated installer: ops builds the ISO (`nix build .#installer-pbs`; `proxmox-auto-install-assistant` is in nixpkgs) with the answer file from git | the official appliance and upgrade path, installed no-touch like the NixOS hosts, and rebuildable from git alone | PBS on NixOS (shelved, Open); cleaning CT 240 in place (it keeps v1's users and history); building the ISO on CT 240 (packages installed by hand, and a rebuild would need a running PBS) |

**Drive's limits** (rclone's docs): 750 GiB uploaded a day, about 2 new files a second, and 10
requests a second per client.
- restic's 64 MiB packs (`pack-size`) keep the file count down.
- The first PBS sync may take days. It resumes each night (`--max-transfer 700G --cutoff-mode soft`).

### Prechecks (agent, read-only; Ali where noted)

- **PBS** (done 2026-10-24, as root):
  - datastore `unraid` on NFS from Unraid (`10.10.20.20:/mnt/user/pbs-backups`);
  - 233 GB on disk in 135k chunks, for 9.6 TB of guest data;
  - every chunk encrypted client-side by PVE;
  - prune at 05:00 and 05:15 (keep 14 daily, 8 weekly, 12 monthly), verify daily, GC Sundays 06:00;
  - v1's leftovers: 15 groups of retired or vanished guests (203 snapshots), pruned by the agent at
    Ali's request and garbage-collected (2026-10-24), so only the 8 current guests' groups remain;
    user `svc-ops@pbs` and v1's `root@pam` tokens stay with CT 240;
  - PBS 4.2.8 is installed but 4.2.5 runs (services never restarted); CT 240 retires as it is.
- **PVE** (2026-10-24): the backup jobs leave out the retired guests (core: 10015, 9000, 9090, 731,
  751; network: 635, 730, 750, 837), and core's also Unraid and CT 240. Both nodes' `pbs-unraid`
  entries use one encryption key, stored in Ali's password manager.
- **Drive** (Ali, 2026-10-25, `rclone about gdrive:`): 1.48 TiB free of 2 TiB. The copies need
  about 0.2 TiB: twice the datastore (86.8 GiB) plus the app data (about 6 GB).
- **The uplink** (2026-10-25, 00:05): about 207 Mbit/s up (1 GB from ops to Cloudflare over four
  streams; 130–270 on one). So Drive's own pace sets the first sync's length: it ran at 0.8 new
  files a second (about 1.8 MiB/s, 2026-10-25), so the datastore's 41,202 files take about 14
  hours.
- **Unraid** (Ali): a new share `pbs` for the new datastore, its own so v1's can be removed without
  touching it. Its NFS export: VM 2040 read-write with `no_root_squash` (PBS creates the
  datastore as root, then hands it to user `backup`), and docker-admin read-only for the offsite
  copy, every read as uid 34 (`10.10.50.40(sec=sys,ro,all_squash,anonuid=34,anongid=34)`): the
  datastore's folders are `750`, `backup`'s own. CT 240 reads `pbs-backups` through the core node's
  mount (10.10.50.11), so its move to .39 needs no rule.
- **Egress:** both Docker hosts reach Google's APIs on :443 (rule 810).
- **docker-dmz's disk** (2026-10-25): 128 GB, one ext4 root, 34 GB used: `/opt` 8.9 GB, Docker
  21.6 GB (23 images, all in use), the Nix store 3.3 GB, logs 0.1 GB. 25 GB stays on root once the
  app data moves.
- **Core's `local-lvm`** (2026-10-25): a 348 GiB thin pool, 73% used (94 GiB free), holding 682 GiB
  of guest disks in all, 346 GiB of them v1's stopped guests, which P7 destroys. A disk takes pool
  space only for what is written, and docker-dmz trims weekly.
- **docker-dmz's `/opt/appdata`, for the copy to ops** (2026-10-25): 8.7 GB in 18,258 entries, with
  no ACLs, extended attributes or hard links, so `tar` with numeric owners carries it whole. It
  skips the 13 sockets, which the apps make again. ops has 38 GB free, and one ssh stream from
  docker-dmz carries 110 MB/s: under 2 minutes each way.
- **Re-pulling docker-dmz's images** after its rebuild: 10 of its 21 come from Docker Hub, well within
  its 100 anonymous pulls per 6 hours; the rest from ghcr.io and lscr.io.
- **doco-cd 0.129.1 and held services** (2026-10-25, the first `backup` run): a poll 4 seconds into
  the stop found five held stacks stopped, took it for drift and redeployed them mid-backup (jikan
  with its MongoDB, karakeep, librespeed, marinara). The next poll waited for the job, as designed.
  Hence hot backups, and restores that pause doco-cd themselves.
- **Checked for the hot design** (2026-10-25):
  - PBS's freeze: QEMU's guest agent ignores `EBUSY` from a filesystem mounted twice, so btrfs's
    top level and `@appdata` can both be mounted;
  - btrbk's NixOS timer allows 10 minutes of slack by default (`AccuracySec`), and its service runs
    as user `btrbk`, with sudo for `btrfs`;
  - Docker binds the target of a relative `latest` symlink (tested on docker-dmz);
  - sops-nix hands dotenv and INI secrets over whole: it ignores `key` for both;
  - nixpkgs-unstable's restic is 0.19.1, the image's; 26.05 has 0.18.1.

### Drive access (Ali, once)

From rclone's "Making your own client_id":
1. In Google Cloud console, create a project (`skynet-backup`) and enable the Google Drive API.
2. Google Auth Platform:
   - audience External, with an app name and your email;
   - data access: only `https://www.googleapis.com/auth/drive.file`, a non-sensitive scope, so
     Google needs no verification;
   - add yourself as a test user.
3. Clients → Create → Desktop app. Note the client ID and secret.
4. Audience → **Publish app**. While in Testing, Google expires the refresh token after 7 days. If
   Publish is greyed out, Branding first wants a home page, a privacy-policy URL (two pages on
   `aliammar.net` will do) and `aliammar.net` as an authorized domain.
5. On the workstation, `nix shell nixpkgs#rclone -c rclone config`:
   - a new remote `gdrive`, type `drive`;
   - the client ID and secret, scope `drive.file`;
   - log in in the browser. This writes `~/.config/rclone/rclone.conf`.
6. Into sops for each consumer, then delete the plaintext:
   `nix shell nixpkgs#sops -c sops encrypt --filename-override stacks/dmz/backup/rclone.sops.conf --input-type ini --output-type ini ~/.config/rclone/rclone.conf > stacks/dmz/backup/rclone.sops.conf`.
   Do the same for `stacks/admin/backup/` and `stacks/admin/pbs-offsite/`.

### App data: `stacks/<host>/backup/` (docker-dmz and docker-admin)

One stack per Docker host: two doco-cd `one_off` jobs on the pinned resticprofile image, both
reading `profiles.yaml` from git. Nothing stops.
- **`backup`**, nightly at 04:30, after the guests' PBS backups:
  - its source is a read-only `/opt/appdata`. On docker-dmz that is the newest btrfs snapshot
    (btrbk, 04:20; next section), mounted there so restic sees the live paths. On docker-admin it
    is the folder itself, whose one database is Authelia's small SQLite file;
  - `run.sh` refuses a source with no app data (the dot files at its top, the stamp and the marker,
    don't count: an app's folder must hold something), one without `/opt/appdata/.data-ready`
    (a restore under way or failed, or a fresh host), and on docker-dmz a snapshot more than an hour
    old (from the stamp `/opt/appdata/.snapshot-stamp`, written just before each snapshot). Any of
    them would become the night's snapshot, and retention would age the real ones out;
  - then `resticprofile backup`, with retention (forget) right after it;
  - repository `rclone:gdrive:skynet/restic/<host>`, 64 MiB packs;
  - keeps 7 daily, 4 weekly and 12 monthly snapshots.
- **`check`**, Sundays at 10:00: prune, then `restic check --read-data-subset 5%`.

**Consistent without stopping.** A snapshot holds every app's files at one instant: the state a
power cut leaves. SQLite (most apps) commits atomically, CouchDB (obsidian) only appends, and
MongoDB (jikan) replays its journal, so each restarts from it cleanly. An app caught between two
writes that no transaction ties together (karakeep saving a file, then its row) is no worse off
than after a power cut. PBS's VM backup at 03:30 freezes the filesystems first: a second,
independent copy.

**Not backed up** (`excludes.txt`), because their READMEs class them `cache` (or disposable) and
they rebuild themselves:
- `aiometadata/cold-store`, `aiometadata/poster-cache` and `aiometadata/redis`;
- `jikan/redis` and `jikan/typesense`;
- `karakeep/meili`;
- Gatus's history;
- the doors' certificates.

**Files:**
- `compose.yaml`, `profiles.yaml`, `excludes.txt`, and `run.sh` (the jobs' entrypoint, the same on
  both hosts; `APPDATA_SNAPSHOT=true` on docker-dmz turns on the snapshot's age check);
- `.doco-cd.yml`: reconciliation off, as for every stack of jobs only;
- `secret.sops.env`: `RESTIC_PASSWORD` (agent-generated) and `HC_PING_URL`;
- `rclone.sops.conf` (Ali's).

`skynet-restore` reads the same two sops files on the host, through sops-nix.

**Mounts:**
- the source at `/opt/appdata`, read-only. On docker-dmz it is `/mnt/appdata-pool/@snapshots/latest`
  with `create_host_path: false`, so a missing snapshot fails the job instead of handing it an
  empty folder;
- restic's cache on the host's ext4 (`/var/cache/restic-appdata`), outside the snapshots.

The job copies `rclone.conf` somewhere writable at start, since rclone saves refreshed tokens.

**Notes:**
- A new stack needs nothing here beyond its cache paths in `excludes.txt`.
- restic sees the same paths every night, so it takes the night before as its parent and reads only
  what changed.

### docker-dmz: `/opt/appdata` on btrfs (`hosts/docker-dmz/disk.nix`)

- **Layout** (disko; Ali's sizes, 2026-10-25). The VM's disk grows from 128 to 193 GiB
  (`proxmox.sh`), thin on core's `local-lvm`:
  - ESP, 512 MiB;
  - root, ext4, **64 GiB**: NixOS, the Nix store, and Docker's images and containers (25 GB
    today). Docker stays on ext4, where its usual storage driver belongs. Its images alone are
    21.6 GB, and the weekly prune keeps a replaced image for 7 days, so a round of updates can
    double them for a week;
  - the rest, **128 GiB**, **btrfs** (label `appdata`, `noatime`): its top level at
    `/mnt/appdata-pool` for btrbk, subvolume `@appdata` at `/opt/appdata`, and subvolume
    `@snapshots`. No `nofail`: if the btrfs doesn't mount, the host stops at boot instead of
    starting the apps on an empty folder.
- **Snapshots** (btrbk, `services.btrbk.instances.appdata`, `snapshotOnly`):
  - at 04:20, read-only `@snapshots/@appdata.<YYYYMMDDThhmm>`. The module's timer allows 10 minutes
    of slack; here 1 minute, so the snapshot always comes before 04:30;
  - every snapshot is kept for 2 days, then one a day for 7 (`snapshot_preserve_min 2d`,
    `snapshot_preserve 7d`); btrbk always keeps the newest;
  - before each run, the stamp; after it, `@snapshots/latest` pointing at the newest. Both run as
    root (systemd's `+`), since btrbk itself runs as user `btrbk`.
- **PBS** freezes `/` and `/opt/appdata` through the guest agent before the VM backup. The top level
  mounted as well is fine: the agent ignores the second freeze's `EBUSY`.
- **docker-admin** keeps its ext4 layout. Its data worth keeping is about 1 MB (Authelia), and a
  direct copy at 04:30 serves.

**The rebuild** (done 2026-10-25; the apps were down from 17:37 to 19:23). disko can't reshape a
running disk and ext4 can't shrink while mounted, so docker-dmz is rebuilt from git with the new
layout (`runbooks/new-vm.md` → Rebuild). Its data goes to ops and back (Ali, 2026-10-25): a cold
copy, exact, caches included, and minutes each way. Restores from Drive are drilled per stack (PRs
and order, step 6), and P7's drill rebuilds a Docker host from backup.

Before: the hot backups PR (PRs and order, step 5) is ready with CI green, and docker-dmz's
installer ISO is built from its branch.
1. **Agent**, old docker-dmz: doco-cd and every stack stopped, then `/opt/appdata` copied to ops as
   one tar (`~skynet/rebuild/docker-dmz-appdata.tar`) and compared with it file by file. The stacks
   stay stopped.
2. **Ali**: a PBS backup of VM 10010, the fallback.
3. **Ali**: `qm stop 10010 && qm destroy 10010`.
4. `runbooks/new-vm.md` steps 1–6 on the PR's branch:
   - its `proxmox.sh` creates VM 10010 with the 193 GiB disk;
   - the installer boots, and the agent records its new host key (`ssh_host.pub`, the `.sops.yaml`
     recipient, the agent's pin);
   - Ali re-encrypts docker-dmz's 19 files for it (`rclone.sops.conf` with `--input-type ini`:
     sops doesn't know `.conf`), the agent checks each file's recipients, then Ali merges:
     `nix shell nixpkgs#sops -c sh -c 'for f in secrets/docker-dmz.yaml stacks/dmz/*/*.sops.*; do case "$f" in *.conf) sops updatekeys -y --input-type ini "$f" ;; *) sops updatekeys -y "$f" ;; esac || echo "FAILED: $f"; done'`;
   - the install from `main`, with `--copy-host-keys` and doco-cd held (Restores).
5. **Agent**: the tar back into `/opt/appdata`, now on btrfs, and compared again; then the first
   local snapshot (`systemctl start btrbk-appdata`); then doco-cd released, which re-pulls the
   images (22 GB) and starts the stacks on their data.
6. **Agent**: `systemctl --failed` empty and Gatus green; a first hot backup, started by hand; then
   the app-data drill (PRs and order, step 6). The copy on ops goes once Ali says so.

Fallback: until step 3 nothing has changed. After it, Ali restores 10010 from step 2's backup
**without starting it**, the merge is reverted on `main` (the old layout, and the old host key's
recipients), then he starts it.

### Restores: `skynet-restore` (glue on both Docker hosts, from `modules/docker-host.nix`)

It runs as root on the host: `ssh -t <you>@<host> sudo skynet-restore …`. On docker-dmz the agent
can run it too (D11). It needs neither doco-cd nor the jobs' containers. It uses rsync for local
snapshots, and restic 0.19 (nixpkgs-unstable, the image's version) for Drive, with the backup
stack's own sops files decrypted on the host by sops-nix. sops-nix hands a dotenv file over whole,
so it reads `RESTIC_PASSWORD=` out of it.
- `skynet-restore list [<stack>]`: the local snapshots (docker-dmz) and the Drive snapshots; with a
  stack, how many entries each Drive snapshot changed in it.
- `skynet-restore local <stack> <snapshot>`: from a local snapshot, on docker-dmz. It takes seconds,
  with no download. The snapshot is always named, never "newest": after a restore, the newest is
  the one taken just before it.
- `skynet-restore drive <stack> [<snapshot>]`: from Drive, `latest` by default.
- In place, from either source:
  1. it checks that the stack's folder is in the snapshot;
  2. on docker-dmz it takes a snapshot first (btrbk's unit), so the restore can be undone, and
     prints `skynet-restore local <stack> <that snapshot>`;
  3. it holds doco-cd: it takes `/opt/appdata/.data-ready` away (below), after writing a record
     of the restore (`/var/lib/skynet/restore-held`: the stack, the undo snapshot, then each
     container it stops). doco-cd's systemd condition then fails whatever starts it: a NixOS
     switch (which starts every wanted unit again) or a reboot. Then it stops doco-cd, so no poll
     or reconciliation restarts the stack mid-restore;
  4. it stops the stack's containers: every container of its Compose project, caches included;
  5. it puts `/opt/appdata/<stack>` back exactly as in the snapshot. From a local snapshot that is
     `rsync --delete`, comparing contents; from Drive, `restic restore
     <snapshot>:/opt/appdata/<stack> --target /opt/appdata/<stack> --delete`. Only the stack's
     folder is the target, and its cache folders (`excludes.txt`) are neither restored nor deleted;
  6. it puts the marker back, starts the containers again, then doco-cd, and deletes the record.
- **A failed restore holds the host.** Failing before step 5 changed a file, it puts everything
  back as it was. Failing after, it leaves the stack stopped and doco-cd held: the stack's data is
  half one snapshot and half the other, and no app should start on that. It prints how to end the
  hold, and `skynet-restore list` repeats it. The same restore again (another snapshot is fine),
  its undo (`skynet-restore local <stack> <undo snapshot>`) or `--all` may run, and the first to
  succeed does step 6, starting everything the failed run stopped. A restore of another stack is
  refused meanwhile. Ending it by hand (accepting the data as it is):
  `rm /var/lib/skynet/restore-held && touch /opt/appdata/.data-ready && systemctl start
  docker-doco-cd`; doco-cd's first poll then redeploys the stopped stack.
- `--to <dir>`, either source: into a scratch folder, with nothing stopped or paused (drills, or one
  file).
- `--all`, either source: every stack. On a rebuilt host doco-cd is still held (below): it restores
  every stack, takes the first local snapshot (docker-dmz), then releases doco-cd, which deploys the
  stacks onto their data.
- One restore runs at a time (a lock). Restoring one stack leaves the others running.
- **doco-cd waits for the data.** It starts only once `/opt/appdata/.data-ready` exists (a systemd
  condition in `modules/docker-host.nix`, after `/opt/appdata`'s mount). A fresh install's
  `/opt/appdata` is empty, and so is a wiped data disk's, so no app starts on nothing: an empty
  CouchDB, say, offered to Obsidian's sync. A forgotten step leaves the apps stopped, not empty.
  - The marker is written last, once the data is complete. `skynet-restore … --all` writes it after
    every stack and the first local snapshot (docker-dmz); a failed `--all` writes none. A restore
    in place takes it away while it works (step 3), and the backup job refuses a source without it.
  - The copy to ops leaves it out, so it can't arrive halfway through the copy back.
  - On a brand-new host, or after data copied back from ops, it's written by hand
    (`runbooks/new-vm.md`, step 6): on docker-dmz after a first `systemctl start btrbk-appdata`, so
    the backup job finds `latest`.

**Gotchas:**
- A restored stack keeps its cache folders as they were. One whose search index is a cache
  (karakeep's meilisearch) may need a reindex.
- While doco-cd is held, its jobs wait too, the heartbeat included: a long `--all` may page
  healthchecks.io's heartbeat check once, and a failed restore pages it until the hold ends.
- A Drive restore during Sunday's 10:00 prune fails on restic's lock; run it again after.

### PBS, greenfield: VM 2040 (`pbs/`)

CT 240 carries v1: its users, its retired guests' history, and PBS backing itself up. A new PBS
starts clean beside it, with its config in git from the first day. CT 240 goes with v1's backups
once both nodes back up to the new one (Ali, 2026-10-25: they aren't needed).
- **VM 2040** on the core node, at 10.10.20.40 (VLAN 20), CT 240's address, so `HOST_PBS`, its
  firewall rules and the Gatus row carry over: 2 vCPU, 4 GB with 2 GB guaranteed (ballooning:
  verify, GC and backups use the rest), and a 32 GB OS disk on `local-lvm`. `pbs/proxmox.sh` is the
  `qm create`, as for the NixOS hosts. Core's backup job leaves it out: PBS rebuilds from git.
- **A second NIC on VLAN 50**, 10.10.50.24: the nodes' storage `pbs` points there, so backups and
  restores don't cross OPNsense, which runs on the network node. Each address answers by its own
  VLAN, and PBS's own firewall guards that NIC (`pbs/README.md` → Network).
- **Install:** Proxmox's automated installer. `pbs/answer.toml` holds:
  - the disk, address, hostname, and the NIC by its MAC (named `lan`);
  - root's SSH keys (the agent's, from ops only, and Ali's);
  - the hash of a random root password (agent-generated straight into `pbs/secret.sops.yaml`, for
    Ali).

  ops builds the ISO (`nix build .#installer-pbs`: Proxmox's PBS 4.2-1 ISO, pinned by its checksum,
  with the answer built in), and Ali boots the VM from it. It installs itself; then `pbs/setup.sh`
  (the agent, as root) adds the no-subscription repository, the guest agent, the datastore's NFS
  mount and `pbs/etc/`. Step by step: `pbs/README.md`.
- **Datastore `skynet`:** a new Unraid share `pbs` (`/mnt/user/pbs`), mounted at
  `/mnt/datastore/skynet` on first use, with namespaces `core` and `network`.
- **Config from git** (`pbs/etc/`, below):
  - prune per namespace, keeping 14 daily, 8 weekly and 12 monthly, as now;
  - verify daily (verified snapshots skipped, re-verified after 30 days);
  - GC on Sundays at 12:00, after the offsite run.
- **Users:**
  - `root@pam` (Ali in the UI; the agent over SSH, D11);
  - `pve@pbs`, with tokens `core` and `network`, each `DatastoreBackup` on its own namespace. The
    user holds it on both, since a token never gets more than its user.

  Nothing else. The tokens arrive from `pbs/etc/` without secrets; Ali regenerates each one into
  its node's storage entry.
- **Cutover** (Ali, PVE config), on each node:
  - add storage `pbs`: the new server, its token, and a new client-side encryption key (PVE
    generates it; it goes in the survival kit);
  - point the backup job at it. The jobs already leave out the retired guests until P7 destroys
    them (Prechecks).

  The first night writes full backups into the new datastore.
- **v1's PBS** (Ali): CT 240 moved to 10.10.20.39 to free .40 for VM 2040, and `HOST_PBS` holds
  both addresses meanwhile. Once both backup jobs write to `pbs`, it all goes: each node's
  `pbs-unraid` storage, CT 240, the core node's NFS mount of `pbs-backups` (`/mnt/pbs-unraid`,
  CT 240's `mp0`), .39 from `HOST_PBS`, and the share with v1's datastore.

### PBS offsite: `stacks/admin/pbs-offsite/` (docker-admin)

- **Mount** (`hosts/docker-admin`): the datastore's share (`/mnt/user/pbs`) over NFS 4.2,
  read-only, soft and automounted, at `/mnt/pbs-datastore`. Binding it at a job's start mounts it
  (tested 2026-10-25). Unraid's export maps docker-admin to uid 34, PBS's `backup`, which owns the
  datastore's `750` folders.
- **Job `sync`** (`one_off`, daily at 06:00): after both nodes' backups and the prune, and outside
  GC (Sundays 12:00) and verify.
  - It runs `rclone sync /mnt/pbs-datastore gdrive:skynet/pbs`. The chunks are already encrypted, by
    PVE's keys.
  - Flags: `--transfers 4 --tpslimit 8 --drive-chunk-size 64M --max-transfer 700G --cutoff-mode soft`.
    Exit 8 (the transfer limit reached) counts as a success: the next night carries on.
  - It leaves out the datastore's lock and GC-status files, and the temporary files PBS renames into
    place (`*.tmp`, `*.tmp_*`).
  - It refuses to run unless the source holds `.chunks/0000`: an unmounted share is an empty folder,
    and syncing one would empty Drive's copy.
- **Job `check`** (Wednesdays 10:00): `rclone check --one-way` against the datastore, by hash.
- **What Drive sees:** PVE encrypts each guest's disks, config and log. Each snapshot's manifest is
  only signed, so the guests' IDs, names (the notes), sizes and times, and the keys' fingerprints
  show. Files the datastore drops sit in Drive's trash for 30 days.
- **A guest from Drive** (site loss, or the drill): `runbooks/restore.md`, case 6. For one guest,
  Drive's copy is mounted (`rclone mount --vfs-cache-mode full`) and a scratch datastore reads its
  chunks, so only those the restore needs are fetched; after a site loss, the whole copy goes into
  a datastore PBS made.

### PBS's config in git: `pbs/etc/`

PBS stays Proxmox's appliance (VM 2040, Debian), but its settings live in git, the way OPNsense's do
(os-git-backup to `skynet-opnsense`).
- **`pbs/etc/`** mirrors the part of PBS's `/etc` that git holds; `pbs/setup.sh` installs it:
  - `proxmox-backup/`: its config files without secrets, from an allowlist: `datastore.cfg`,
    `prune.cfg`, `verification.cfg`, `sync.cfg`, `acl.cfg`, `user.cfg`, `domains.cfg`, `node.cfg`,
    `notifications.cfg`, `traffic-control.cfg`, `media-pool.cfg`, `tape.cfg` and `tape-job.cfg`.
    CT 240's live folder (2026-10-24) held six of them and otherwise only secrets. Never the
    secrets: `shadow.json`, `token.shadow`, `tfa.json`, keys and certificates, `*-priv.cfg`,
    `remote.cfg` (passwords), `s3.cfg` and `metricserver.cfg` (keys, tokens);
  - the datastore's NFS mount units, the apt sources and `resolv.conf`.
- **Changes:** a change on PBS, whether the agent's (root, D11) or one in its UI, is followed by its
  PR (rule 2). Or a PR first, then `setup.sh` after the merge.
- **Drift:** a daily timer on ops (`modules/pbs-drift.nix`, 07:00) copies these files, and every
  allowlisted name, from PBS over SSH and compares them with `main`'s as deployed on ops. A
  difference, or a failed check, goes to `#alerts`, naming the files.
- **Rebuild:**
  - a fresh PBS from `pbs/answer.toml`, then `pbs/setup.sh`, which copies these files back and
    reuses the datastore on Unraid as-is;
  - Ali regenerates the two tokens' secrets into PVE, whose storage entries take the new
    fingerprint;
  - the agent updates the host key's pin and caddy-admin's pinned cert (`pbs/README.md`).

### Monitoring

- **healthchecks.io:** Ali creates three checks, each daily: `backup docker-dmz` and
  `backup docker-admin` (grace 3 h), and `pbs-offsite` (grace 6 h). Their ping URLs go into the
  stacks' secrets, and their badge URLs into Gatus's. resticprofile pings start, success and
  failure; the rclone job pings with curl.
- **Gatus:** one job row per check from its badge, as for the heartbeats.
- **`#alerts`:** `notify_on: failure` on every job.
- **btrbk:** a failed snapshot fails the next backup (the snapshot's age check), which alerts like
  any failed night.

### Survival kit (Ali, outside the lab)

- the restic passwords, one per host;
- PVE's PBS encryption keys, one per node (Datacenter → Storage → `pbs` → Encryption: download).
  Without them every copy, on Unraid or on Drive, is unreadable;
- the OAuth client's ID and secret (logging in again gives a new token);
- PBS's root password (`pbs/secret.sops.yaml`);
- the age master key.

Copy them with `nix shell nixpkgs#sops -c sops -d <file>` on the workstation, into the password
manager.

### PRs and order

1. **Ali:** the Prechecks' answers, Drive access, and the three healthchecks.io checks. Done
   (2026-10-25).
2. **PBS greenfield PR:** done (#75). VM 2040 runs from it, and v1's PBS is gone.
3. **App backups PR:** done (#76): both `backup` stacks, `skynet-restore` and the Gatus rows, cold at
   first (`stop_services`).
4. **PBS offsite PR:** done (#78): the NFS mount, `pbs-offsite` and its Gatus row. The first sync
   (from 2026-10-25 13:38) takes about 14 hours: the datastore held 41,202 files (86.8 GiB) after
   its first full backups, and Drive takes about 0.8 new files a second.
5. **Hot backups PR:** done (#81), merged inside docker-dmz's rebuild (2026-10-25). The data went
   to ops and back in under 3 minutes each way, copy and compare, with no difference either time.
6. **Drill:** done (2026-10-25), on docker-dmz:
   - `skynet-restore local librespeed <snapshot>` (8 s) and `skynet-restore drive librespeed`
     (26 s), both in place. Each removed a marker file the snapshot lacked and left the folder
     equal to the snapshot;
   - `skynet-restore drive karakeep --to` a scratch folder (75 s): 1.79 GiB in 414 files, no
     difference from the live folder.
7. **Drill:** done (2026-10-27): technitium-core (7051) from Drive's copy of its 10-27 backup,
   restored beside itself as VM 99051 (`runbooks/restore.md`, case 6). PBS verified its 888
   chunks through a read-only mount of Drive (0 errors; 916 MiB in 300 s, 8 readers), PVE
   restored the 16 GiB disk in 110 s, and the VM booted and answered as technitium-core. A
   cloud-backed datastore needs `chunk-order=none` and parallel readers: Drive answers each chunk
   in about 2 s.

### Exit criteria

- Seven green nights in a row, for all three jobs, docker-dmz's snapshots and VM 2040's backups. CT
  240 is gone.
- Both drills done (app data from both sources, and a guest from Drive), with evidence in their PRs.
- Ali confirms the survival kit is stored.
- `pbs/etc/` matches PBS, and the drift check is quiet.
- `runbooks/restore.md` covers six cases: an app from a local snapshot, an app from Drive, a host, a
  guest, PBS rebuilt from `pbs/etc/`, and a restore from Drive with nothing else left.

**Open:**
- Whether any Unraid shares need offsite too (not part of this phase).
- doco-cd: report upstream that a poll can redeploy services a running job holds stopped (0.129.1,
  Prechecks). With hot backups and restores that pause doco-cd, the lab no longer relies on it.
- A failed guest backup reaches only PVE's built-in sendmail to root's address, and a failed
  verify or GC on PBS only root's local mailbox (no relay): nothing posts them to `#alerts`. A
  webhook target there on each (Ali pastes the URL; PBS's `notifications.cfg` then joins git)
  would.
- PBS as a NixOS VM: shelved (Ali, 2026-10-24); its config goes to git meanwhile (`pbs/etc/`). nixpkgs has only the client. A community package and
  module (nixos-pbs, PBS 4.2.3, from source in an FHS wrapper) has had a few testers since
  2026-06, with its nixpkgs PR open. Once it lands, trial it beside the current PBS: a sync job
  into its own datastore, verify, a restore drill. Move only when that holds, by pointing it at
  the existing Unraid datastore; PVE's storage entry then changes (Ali).

## P5 — Observability `[detailed]`

**Goal**
- VictoriaMetrics on docker-admin collects metrics from every host, container, backup job and
  deploy tool. VictoriaLogs collects every host's journal, the containers' logs included.
- Rules in git turn both into alerts in `#alerts`, through Alertmanager. A watchdog alerts from
  outside when the alerting itself stops.
- Grafana shows it all behind the admin login, its dashboards from git.
- The agent reads both through their official MCP servers, so "why is X slow?" and "what happened
  at 03:00?" are queries, not guesses.

**Why now:** P6 verifies its changes and rolls them back on these numbers. P5 also closes P4's gap:
today a failed, missed or disabled guest backup posts nothing (P4 → Open).

### Tools (researched 2026-10-26)

| Need | Choice | Why | Passed over |
|---|---|---|---|
| Metrics | VictoriaMetrics 1.154, single-node | one binary; Prometheus' scrape config, and PromQL queries work unchanged; a fraction of Prometheus' memory and disk; retention is one flag; a query UI built in | Prometheus (more memory and disk for the same series); Mimir, Thanos (clusters) |
| Logs | VictoriaLogs 1.53 | takes `systemd-journal-upload` natively (`/insert/journald`), so hosts run no shipper of their own; retention by age and by disk space | Loki (needs a shipper: Promtail is retired, Alloy is heavy); Elasticsearch, OpenSearch (gigabytes of memory) |
| Shipping | `systemd-journal-upload` (NixOS `services.journald.upload`; on PBS, Debian's `systemd-journal-remote`) | part of systemd. It keeps a cursor, so after an outage it resumes where it stopped: the journal is the buffer | Vector, Fluent Bit, Alloy (one more daemon per host) |
| The way in for logs | vlagent, VictoriaLogs' own agent, on docker-admin :9429, on the host's network (so the host firewall decides who sends) | it takes the same protocols and has no query API at all, so a host that ships its logs can read no one's; it buffers on disk while VictoriaLogs restarts | VictoriaLogs' own port (it answers queries too); a proxy's path rule (vmauth: one more rule to get right); pulling with `systemd-journal-remote` (no cursor across restarts) |
| Host metrics | node-exporter (NixOS module; Debian's package on PBS) | the standard; its textfile collector carries job results | — |
| Container metrics | cAdvisor 0.56 (NixOS `services.cadvisor`) | the standard: CPU, memory, network and restarts per container; on the host because it reads every cgroup as root | Docker's own metrics (the daemon's, not per container); cAdvisor as a container (privileged, with the host's root mounted) |
| Proxmox | prometheus-pve-exporter | the standard, read-only with a token per node | the nodes' metric-server push (InfluxDB; config on the nodes) |
| PBS | pbs-exporter (natrontech) 0.9 | each guest's newest backup and its verify state, per namespace; read-only. A small project (67 stars), so its own target-down alert says when it breaks | PBS's metric-server push (host and datastore only, nothing per guest) |
| Rules and routing | vmalert, one for metrics and one for logs (as VictoriaMetrics advises) → Alertmanager | Prometheus-format rules in git; Alertmanager's Discord receiver, grouping, inhibition and silences | Grafana's alerting (rules in its database); Gatus for all of it (it checks endpoints, not trends) |
| Dashboards | Grafana, OIDC through admin Authelia | data sources and dashboards provisioned from git | the stores' own UIs alone (kept, for ad-hoc queries) |
| Agent eyes | `mcp-victoriametrics`, `mcp-victorialogs` (VictoriaMetrics' own; images with an HTTP mode) | read-only query tools for Claude Code | — |

### Prechecks (agent, read-only; done 2026-10-26)

- **docker-admin:** 0.8 GB of memory in use (the guest holds 3.5 of its 4 GB just now); `/` has 25
  of 31 GB free.
- **The network node:** 11.6 of 14.5 GiB used: OPNsense 4 GiB (pinned), Omada up to 3, docker-admin
  up to 4, technitium-network 1. The outline's 6 GB docker-admin doesn't fit.
- **Ports:** comin's exporter (:4243, every NixOS host) and doco-cd's metrics (:9120, both Docker
  hosts) already listen, closed by the host firewalls. :9100 is free everywhere; cAdvisor's default
  :8080 is doco-cd's on the Docker hosts.
- **systemd:** 260 on the NixOS hosts, 257 on PBS. Both upload to VictoriaLogs; 258's compression
  and headers aren't needed.
- **PBS:** Debian 13 has `prometheus-node-exporter` 1.9.0 and `systemd-journal-remote` 257. The
  latter enables nothing on install (its listening sockets stay off); `dbus`, which the systemd
  collector needs, is there.
- **Reachability:** docker-admin shares VLAN 50 with both nodes (:8006) and already reaches PBS's
  :8007 (rule 235, for Gatus).
- **cAdvisor and Docker 29:** Docker keeps images in containerd's snapshotter. cAdvisor 0.56.2 (the
  hosts' nixpkgs) names containers only through Docker's own containerd socket
  (`-containerd=/run/docker/containerd/containerd.sock`). Tested on docker-dmz: 23 containers by
  name and compose project, about 1,200 series.
- **Journals:** 2–21 MB a day per host in journald's export format (docker-dmz the most), about
  40 MB a day for the lab before VictoriaLogs compresses it.

### Where it runs (docker-admin)

Four stacks in `stacks/admin/`, each with its site, DNS name, Gatus row and README
(`runbooks/new-stack.md`), and two for Wider eyes, `exporters` and `omada-exporter`, with no site:

| Stack | Containers | Name | `/opt/appdata/<stack>/` |
|---|---|---|---|
| `metrics` | victoriametrics, vmalert, pve-exporter, pbs-exporter, mcp-victoriametrics | `metrics` | `data`: cache (history, not backed up) |
| `exporters` (Wider eyes) | opnsense-exporter | — | none |
| `omada-exporter` (Wider eyes) | omada-exporter | — | none |
| `logs` | victorialogs, vlagent (its syslog listeners: Wider eyes), vmalert-logs, mcp-victorialogs | `logs` | `data`, `buffer`: cache |
| `alertmanager` | alertmanager | `alerts` | `data` (silences): data |
| `grafana` | grafana | `grafana` | `data`: cache (all of it comes from git or the login) |

- **Access:** every name is behind admin Authelia (two factor, Ali). Ops (10.10.90.91) bypasses it,
  as for Gatus's API, only on the query APIs and `/mcp` of `metrics` and `logs`, and on `alerts`'
  silences API.
- **Memory:** about 1 GB for all of it, so docker-admin goes from 0.8 to about 2 GB in use. It keeps
  its 4 GiB; the part guaranteed rises from 2 to 3 GiB (`proxmox.sh`; Ali:
  `qm set 5040 --balloon 3072`).
- **Disk:** about 15,000 series every 30 s comes to 30–45 MB a day, so 13 months of metrics is
  12–18 GB, reached over the year. Logs keep 30 days and never more than 4 GiB
  (`-retention.maxDiskSpaceUsageBytes`). The 25 GB free holds the first months, and docker-admin's
  rebuild in P6 grows its disk to 64 GiB. The first week's growth (`vm_data_size_bytes`) checks the
  estimate.

### Metrics

VictoriaMetrics scrapes every 30 s; Proxmox once a minute and PBS every 5 minutes, since each of
those scrapes is several API calls. Its targets are in `stacks/admin/metrics/scrape.yaml`
(Prometheus' format), which CI checks with the pinned image's `-dryRun`:

| Target | Runs on | Notes |
|---|---|---|
| node-exporter :9100 | every NixOS host (`observability.nix`); PBS (`pbs/setup.sh`) | the systemd collector (failed units) and the textfile collector (job results) |
| cAdvisor :9338 | both Docker hosts (`docker-host.nix`); 8080 is doco-cd's | Docker's containers only, with the compose project as their one label (fewer series) |
| comin :4243 | every NixOS host | fetch, build and deploy failures; `comin_need_to_reboot` |
| doco-cd :9120 | both Docker hosts | its deploys and reconciliations |
| Gatus | docker-admin (`metrics: true`) | each row's result, response time and certificate expiry |
| pve-exporter | `metrics` | both nodes, each with its own token |
| pbs-exporter | `metrics` | PBS, one token |
| the stack itself | docker-admin | VictoriaMetrics, VictoriaLogs, vlagent, both vmalerts, Alertmanager, Grafana |

- **Host firewalls:** each host's exporters admit only docker-admin. On docker-admin, its own
  containers reach them from their bridge.
- **Job results** land in node-exporter's textfile folder (`/var/lib/node-exporter`), which the jobs
  that write there mount:
  - restic: resticprofile's own metrics file (`prometheus-save-to-file`: status, duration, bytes
    added), so config only;
  - the PBS offsite sync: `run.sh` writes its end time and rclone's exit code;
  - btrbk: its hook writes the newest snapshot's time beside the stamp.
- **Tokens (Ali, once):**
  - PVE: `skynet@pve!metrics` on each node, PVEAuditor on `/` (like `read`, but held by
    docker-admin), into `stacks/admin/metrics/pve.sops.yml`: one module per node, only the token
    values encrypted;
  - PBS: user `metrics@pbs` with `DatastoreAudit` on the datastore and `Audit` on `/system`, in
    `pbs/etc/` (git, applied by `setup.sh`). Ali generates its token `exporter`, with the same
    rights, into `stacks/admin/metrics/secret.sops.env`; a rebuild regenerates it
    (`pbs/README.md`).
- **TLS:** the exporters check the nodes and PBS against caddy-admin's pinned certs.

### Logs

- **Every host ships its journal** to vlagent at `http://10.10.50.40:9429/insert/journald`: the
  NixOS hosts from `observability.nix` (`services.journald.upload`), PBS from `pbs/etc/`. vlagent
  runs on the host's network, so docker-admin's firewall admits only the hosts that ship. It
  forwards to VictoriaLogs on loopback; VictoriaLogs answers only inside docker-admin, to its
  containers and the door.
- **Container logs** are already in each host's journal (Docker's journald driver), each line with
  its `CONTAINER_NAME`. That field joins the host and unit as a stream field, so each container is
  a stream of its own.
- **docker-dmz** reaching vlagent is the one opening from the DMZ into the management VLAN: one
  port, from one address, write-only by construction. Ali's call (Firewall and DNS).
- **Retention:** 30 days in VictoriaLogs, capped at 4 GiB; each host keeps its own 2 weeks
  (journald).
- **Floods:** journald on every host drops what one service logs past about 100 lines a second
  (`observability.nix`, PBS's `etc/`) and logs how many it dropped, so a loop can't fill a disk or
  push the oldest days out. Containers share dockerd's allowance: journald keys its limit on the
  sending unit, and every container's lines come from dockerd, so there's no per-container cap.
  `LogFlood` names the container at 50 a second, and `LogsDropped` counts what neighbours lost.
  Admin Authelia logs at `warn`, as the apps' does: an anonymous request is no log line.
- **Freshness:** every host logs a heartbeat line every 5 minutes (`log-heartbeat`), so a host
  whose lines stop arriving shows (`LogsNotArriving`), as does vlagent holding logs back
  (`LogForwardingStuck`) or dropping them (`LogsLost`).

### Alerts

- **Rules** live in `stacks/admin/metrics/rules/` (PromQL, `vmalert`) and `stacks/admin/logs/rules/`
  (LogsQL, `vmalert-logs`: one datasource per vmalert, as VictoriaMetrics advises), trimmed to this
  lab. Each alert's `instance` is its host. Both keep their alerts' state in VictoriaMetrics, so a
  restart doesn't reset a `for` timer. They read it back on their first evaluation only, so each
  starts once its stores answer: a reboot starts containers in no order. CI checks the rules
  (`vmalert -dryRun`) and Alertmanager's config (`amtool check-config`), each with its pinned image,
  and runs the unit tests in `stacks/admin/metrics/rules.test.yml` (`vmalert-tool`): synthetic
  series for the rules whose meaning hangs on how an exporter counts.
- **The first set:**

| Alert | Fires when |
|---|---|
| `HostDown`, `TargetDown` | a host's node-exporter, or any other target, unreachable for 5 min |
| `DiskFull`, `DiskFillsWithinADay` | under 10% free for 5 min; or, under 25% free, full within a day at the last 6 hours' rate |
| `MemoryLow`, `OOMKill` | under 10% available for 10 min; any OOM kill (the kernel's counter, containers' included) |
| `UnitFailed` | a service, socket or timer failed for 5 min |
| `CrashLoop` | a container started 5 times in 15 min, counted from systemd's log of each container start (LogsQL; cAdvisor's start time is the creation, which a restart keeps). The heartbeat jobs start 3 times. doco-cd still restarts an unhealthy one by itself and posts, as now |
| `GuestBackupStale`, `GuestBackupUnverified` | the newest backup of a guest PVE has now, in its node's namespace, older than 26 h (a retired or moved guest's kept backups don't count); or any guest's newest without a passed verify 5 h on (PBS verifies at 04:30, after both nodes' jobs) |
| `GuestNeverBackedUp`, `PbsApiDown` | a guest PVE runs with no backup in its node's namespace for 26 h (Unraid and PBS left out, as in the jobs); pbs-exporter unable to read PBS's API for 10 min, which otherwise leaves the backup alerts quiet |
| `StorageFull`, `DatastoreFull` | a PVE storage or PBS's datastore over 80% |
| `CominFailing`, `DocoCdNotPolling` | comin failing to fetch, evaluate or build main for an hour; doco-cd without a successful poll for 30 min (none ran, or each failed: doco-cd counts both in `polls_total`), except while one of its own jobs, running under 8 h, holds the polls. A failed deploy is the deployer's own post, as now |
| `CertificateExpiring` | a certificate Gatus checks expires within 14 days (Gatus itself alerts at 7) |
| `FilesystemErrors` | ext4, btrfs, I/O or medium errors in a kernel log (every 5 min) |
| `LogFlood`, `LogsDropped` | one container or unit logging over 50 lines a second for 10 min: a loop (journald drops what passes 100); journald reporting lines it dropped |
| `LogsNotArriving`, `LogForwardingStuck`, `LogsLost` | a host seen this week with no heartbeat line in VictoriaLogs for 15 min; over 10 MiB waiting in vlagent for 15 min; vlagent dropping logs |
| `RuleFailing`, `AlertmanagerSendFailing` | a rule failing to evaluate; Alertmanager failing to post to Discord (which can't reach a broken Discord: see `DeliveryWatchdog`) |

- **Alertmanager** (`stacks/admin/alertmanager`, `alerts.aliammar.net`):
  - posts to `#alerts` with its Discord receiver, "Firing: <alert> on <host>" and one line per
    alert; the webhook URL is in its `secret.sops.env` (Ali copies it, as for Gatus);
  - groups by alert and host, and a host that's down mutes its own other alerts (inhibition);
  - `Watchdog` always fires and pings healthchecks.io's check `alertmanager` every minute. If
    vmalert, Alertmanager or docker-admin stops, healthchecks.io posts within 10 minutes;
  - `DeliveryWatchdog` fires only while Discord takes the posts (Gatus's `discord webhook` row
    sees the webhook, and no post failed in 15 minutes) and pings check `alerts-delivery`: a
    deleted webhook or failing posts make healthchecks.io post through its own integrations,
    which don't use the lab's webhook (with email on, it reaches Ali even when Discord is down);
  - the vmalerts' rules and pending alerts: `metrics.aliammar.net/vmalert/` and
    `logs.aliammar.net/select/vmalert/` (each store proxies its vmalert).
- **Not alerted here:** the app-data backups and the offsite copy (healthchecks.io does, as in P4),
  and each failed deploy (comin's and doco-cd's own posts).
- **Gatus** stays the reachability check and posts its own alerts, as now. Its results feed metrics
  for the dashboards and the agent, not more alerts, so nothing posts twice. D8 gains Alertmanager.
- **Silences:** in Alertmanager's UI (`alerts`) or its API. The agent sets one when its own planned
  work would trip an alert: ending within 4 hours, its comment naming the work (an operate verb,
  Rule 4, `AGENTS.md`). Ops reaches the API without a login only to read, set a silence and expire
  one.
- **P4's gap closes:** a failed, missed or disabled guest backup shows as a stale guest within a
  day.

### Grafana

- **`grafana.aliammar.net`, OIDC through admin Authelia,** as P3 did for the apps:
  - admin Authelia gets its OIDC provider: an HMAC secret and a signing key, agent-generated into
    `stacks/admin/authelia/oidc.sops.yml`;
  - Grafana's client: its secret agent-generated into `stacks/admin/grafana/oidc.sops.env`, the
    digest in `oidc-clients.yml`;
  - Ali's account is Grafana's admin, and nobody else gets in. A local admin, its password
    agent-generated, is the break-glass.
- **Provisioned from git** (`stacks/admin/grafana`), read-only in the UI:
  - two data sources: VictoriaMetrics (as Prometheus) and VictoriaLogs (its plugin, version pinned,
    installed before Grafana starts);
  - our boards (`dashboards/lab/`): **Live**, the lab right now every 10 s (hosts, containers,
    Proxmox guests, backups' age, errors and warnings from every host), and **Backups** (each
    guest's newest backup and verify, restic per host, the offsite sync, btrbk);
  - grafana.com's at pinned revisions (`dashboards/upstream/`, `fetch.sh`): Node Exporter Full,
    cAdvisor, Proxmox, VictoriaMetrics, VictoriaLogs, vmalert, Alertmanager.
- **Live tail:** Explore's Live mode on VictoriaLogs (Grafana Live, through the door).

### Agent eyes

- The two MCP servers run in their stacks (HTTP mode, read-only tools) and answer at
  `https://metrics.aliammar.net/mcp` and `https://logs.aliammar.net/mcp`, for ops only (Authelia's
  bypass on `/mcp`).
- `.mcp.json` names both. Their tools ask before each call until Ali allows them in
  `.claude/settings.json`: the agent doesn't grant itself tools.
- P6's scripts read the same data through the plain query APIs.

### Wider eyes (planned 2026-10-28)

The first round watches our own hosts. This one adds what they run on and pass through, so "is
the internet slow?", "is a disk failing?" and "why is this app slow?" are answered from data too
(Ali, 2026-10-28). As before:
- exporters on docker-admin hold any key, and the agent reads only VictoriaMetrics and
  VictoriaLogs;
- every source gets a freshness alert: a dead exporter otherwise leaves the agent blind, silently.

| Source | Metrics | Logs | Set up by |
|---|---|---|---|
| Proxmox nodes | Debian's node-exporter, with its SMART and NVMe textfile timers | the journal, through `systemd-journal-upload`, as PBS's | Ali runs `pve/setup.sh` on each node |
| OPNsense | opnsense-exporter in `exporters`, through a read-only API user | remote syslog to vlagent, TCP 5514: firewall, system, dnsmasq | Ali: the user and its key, the logging target |
| The doors | — | caddy-admin's and caddy-apps' access logs, JSON, into the journal | the PR |
| Unraid | upstream node-exporter and smartctl-exporter, as two Unraid containers | remote syslog to vlagent, TCP 5515 | Ali: the containers (`unraid/README.md`), the syslog target |
| Omada | OmadaBridge in its own stack `omada-exporter`, through a viewer user | its devices' remote logging to vlagent, UDP 5516 | Ali: the user, the logging target |
| Technitium | a timer on each DNS host writes the dashboard's last hour to node-exporter's textfile | already in the journal, every query included (`logQueries`, `dns/README.md`) | the PR |

**Tools** (researched 2026-10-28):

| Need | Choice | Why | Passed over |
|---|---|---|---|
| OPNsense | opnsense-exporter 0.0.19 (AthennaMind; 274★, released 2026-10-21) | gateways' loss and latency, interfaces, pf states and mbufs, services, through OPNsense's API | OPNsense's `os-node_exporter` plugin (the box's CPU and memory, which PVE's view of VM 5001 already gives) |
| Appliances' logs | vlagent's syslog listeners (1.53: the same `vlinsert` VictoriaLogs runs) | no new daemon, and VictoriaLogs stays closed | VictoriaLogs' own listeners (a second way in) |
| Proxmox nodes | Debian 13's `prometheus-node-exporter` and `prometheus-node-exporter-collectors` (smartmon, nvme), `systemd-journal-remote` | what PBS runs; both nodes are PVE 9.2 on Debian 13 | pve-exporter alone (the API's view: no disks, no host I/O, no logs) |
| Unraid | `quay.io/prometheus/node-exporter`, `quay.io/prometheuscommunity/smartctl-exporter` | upstream's images, on Unraid's Docker | ich777's plugins (archived 2026-08); Unraid's API (no Prometheus side) |
| Omada | OmadaBridge (`rcooler/omada_exporter`, MIT; the maintained fork of charlie-haley's) | controller, APs, switches and clients through a viewer user; its MQTT side off | charlie-haley's original (idle since 2024-08) |
| Technitium | a textfile timer on the DNS hosts (glue) | the admin login is already on the host, so no credential moves | the community exporters (39★ at most, and a token to move) |

**Per source:**
- **`exporters`, a stack of its own:** doco-cd redeploys a whole stack when one of its containers
  dies, so two young exporters' crash loops would restart VictoriaMetrics if they sat in `metrics`.
  Here they restart only each other, and a missing key fails only this stack's deploy.
  VictoriaMetrics reaches them on `edge`. OmadaBridge gets a stack of its own (`omada-exporter`):
  it exits when the controller doesn't answer at its start (tested 2026-10-28), so a controller
  outage is a restart loop, which in `exporters` would restart OPNsense's exporter with it.
- **Proxmox nodes:** `pve/setup.sh` and `pve/etc/`, as PBS's. The nodes' config stays Ali's to
  apply; git describes it.
  - node-exporter on the node's VLAN 50 address, with the systemd and textfile collectors; SMART
    and NVMe health from Debian's own timers;
  - the journal to vlagent, journald's flood cap and the 5-minute heartbeat: PBS's files;
  - docker-admin shares VLAN 50 with both nodes, so OPNsense isn't in the way. docker-admin's
    firewall admits them to vlagent.
- **OPNsense:**
  - the exporter's user holds only the pages its collectors read (Diagnostics: Firewall statistics
    and Netstat, Reporting: Traffic, System: Gateways and Status, Status: Services, Lobby:
    Dashboard), and config writes are denied to it, as to ops's `skynet-read`. Of these, only
    Status: Services allows an action (restarting a service), and the key stays on docker-admin.
    Its firmware, cron, Unbound, Kea (dnsmasq serves DHCP), VPN, CARP, ARP and temperature
    collectors are off, so it holds none of their pages, some of which allow actions (an upgrade,
    a cron job);
  - TLS against caddy-admin's pinned cert (`opnsense.pem`, name `OPNsense.internal`). docker-admin
    already reaches OPNsense's API;
  - the remote log: System → Settings → Logging → Remote, 10.10.50.40, TCP 5514, RFC 5424. The
    firewall log runs at about 8 lines a second (2026-10-28), mostly the default rule's passes:
    about 730,000 lines a day, 10–20 MB stored.
- **The doors:** each request as one JSON line holding only its host, method, status, duration,
  size and the URI's first path segment: no headers and no query, since some apps carry tokens in
  their paths (Stremio addons), queries and headers. LogsQL then gives each app's latency and
  errors, with no new series.
- **Unraid:** `unraid/README.md` describes the two containers (Unraid's config isn't in git). Its
  syslog (Settings → Syslog Server → remote server 10.10.50.40, TCP 5515) carries the array's
  events: a disk disabled, a parity check's result. Its array disks (`/mnt/disk*`) fill past 90%
  by design, so `DiskFull` leaves them out; node-exporter's mdadm collector, which misreads
  Unraid's own md driver, is off.
- **Omada:** OmadaBridge reaches the controller as `Omada:8043` (CT 525; caddy-admin's pinned
  `omada.pem`) and reads the site `Omada Network Skynet`. Remote Logging (site settings):
  10.10.50.40, UDP 5516.
- **Technitium:** every 5 minutes, `dashboard/stats/get?type=LastHour`: queries, server failures,
  NX domains, refusals, blocks, drops, clients and cache size.

**Alerts**, each new source's freshness first:

| Alert | Fires when |
|---|---|
| `TargetDown`, `HostDown`, the host rules | as for every host, now for the nodes and Unraid too |
| `ExporterBlind` | opnsense-exporter or OmadaBridge answers but can't read its API, for 10 min (each one's own success metric) |
| `SyslogNotArriving` | an appliance seen this week sends nothing for 15 min (OPNsense's firewall log never pauses that long; Unraid's and Omada's windows set from their measured rates) |
| `GuestBackupFailed` | a node's journal logs a failed vzdump job: P4's open gap closes in minutes, not 26 h |
| `DiskUnhealthy`, `DiskWearing` | SMART not passed or an NVMe critical warning; wear past 80% (nodes, Unraid) |
| `GatewayDown`, `GatewayLossy` | a gateway offline for 5 min; over 5% loss for 15 min |
| `FirewallStatesHigh` | pf states over 80% of the limit |
| `DnsFailing` | server failures over 5% of the last hour's queries |

**Cost:** two small containers (about 50 MB) and about 8,000 more series. That takes the 13-month
disk estimate from 12–18 GB to 18–27 GB, past docker-admin's 20 GB free before P6's rebuild grows
its disk to 64 GiB: the 11-03 check says which comes first. Logs: about 30 MB a day more, mostly
OPNsense's, inside the 4 GiB cap at 30 days.

### Homepage (at Ali's call)

`home.aliammar.net` behind admin Authelia: links to every admin UI and app, with Gatus's status,
its config in git. Widgets that need tokens wait.

### Firewall and DNS (agent drafts, Ali applies)

- **Aliases:** `ROLE_METRICS_TARGETS` and `ROLE_LOG_SHIPPERS`, each `HOST_SKYNET_OPS`,
  `HOST_DOCKER_DMZ`, `HOST_TECHNITIUM_NETWORK`, `HOST_TECHNITIUM_CORE`, `HOST_PBS`; `PORT_METRICS`
  = 9100, 9338, 4243, 9120 (node-exporter, cAdvisor, comin, doco-cd).
- **Rule 236:** pass TCP `HOST_DOCKER_ADMIN` → `ROLE_METRICS_TARGETS` : `PORT_METRICS`, unlogged
  (a scrape every 30 s per target).
- **Rule 237:** pass TCP `ROLE_LOG_SHIPPERS` → `HOST_DOCKER_ADMIN` : 9429, unlogged. For docker-dmz
  this is the DMZ's one opening into the management VLAN (Logs).
- The Proxmox nodes share docker-admin's VLAN, and rule 235 already covers PBS's :8007.
- DNS: `metrics`, `logs`, `alerts`, `grafana` (and `home`) → 10.10.60.60, each with its PR.
- **Wider eyes:** the nodes, Omada's controller and OPNsense's own address share VLAN 50 with
  docker-admin, and docker-admin already reaches OPNsense's API: none of them needs a rule. Unraid
  does (wave 2): `HOST_UNRAID` joins `ROLE_METRICS_TARGETS` and `ROLE_LOG_SHIPPERS`, `PORT_METRICS`
  gains 9633 (smartctl-exporter), and rule 237's port becomes an alias `PORT_LOG_INGEST` (9429,
  5515). Omada's devices need rule 237 for UDP 5516 only if they sit outside VLAN 50.

### PRs and order

1. **Ali:** the PVE and PBS tokens; healthchecks.io's check `alertmanager` (period 1 min, grace 10
   min); docker-admin's balloon.
2. **Metrics and logs PR:** the `metrics` and `logs` stacks with their sites, DNS and Gatus rows;
   every host's exporters and journal upload (`observability.nix`, `docker-host.nix`, `pbs/`); the
   job metrics. Ali applies the firewall rules.
3. **Alerts PR:** both vmalerts and their rules, Alertmanager, the CI checks, the silences verb.
   Then the tests (Exit criteria).
4. **Grafana and agent eyes PR:** admin Authelia's OIDC provider, Grafana and its dashboards; the
   MCP servers and `.mcp.json`. Two real questions answered from the data, in the PR.
5. **Homepage**, at Ali's call.
6. **Wider eyes, plan:** this section. Merging it is Ali's go.
7. **Wider eyes, wave 1 PR:** `pve/` and the nodes' targets; the `exporters` stack with
   opnsense-exporter, and vlagent's syslog listener; the doors' access logs; their alerts and
   freshness checks. Ali: OPNsense's API user (its key into `stacks/admin/exporters/secret.sops.env`)
   and logging target, then `pve/setup.sh` on both nodes.
8. **Wider eyes, wave 2 PR:** Unraid, Omada and Technitium, with their alerts. Ali: Unraid's
   containers and syslog target, Omada's viewer user (into
   `stacks/admin/omada-exporter/secret.sops.env`) and remote logging, and the alias changes.

### Exit criteria

- Every scrape target is up, and every host's journal reaches VictoriaLogs, docker-dmz's through
  vlagent.
- The agent answers "why is X slow?" and "what happened at 03:00?" from the data (PRs and order,
  step 4).
- Each test fires in `#alerts` and clears: docker-dmz's disk filled (`fallocate`, then removed); an
  exporter stopped; Alertmanager stopped, so healthchecks.io posts.
- Grafana opens behind the admin login, with data sources and dashboards from git alone.
- After a week, docker-admin's memory and disk growth match the sizing, or this section says what
  they are.
- Every Wider eyes source is in, and its freshness alert tested: the source stopped, the alert
  posted, then cleared.
- Two real questions answered through the MCP tools themselves: one about the network, one about
  storage.

**Open:** HAOS (its built-in Prometheus integration); checks that do an app's real work (a search,
a stream lookup), each with a read-only app token (Ali: later).

## P6 — Agent autonomy `[detailed]`

**Goal**
- Ali says "deploy X" or "restore Y to how it was yesterday" in Discord or the Claude app. The agent
  does the rest and reports.
- Updates land by themselves when nothing looks wrong: reviewed, merged in a nightly window just
  after the snapshots, verified, and rolled back, code and data, if they break. A major or breaking
  one reaches Ali as research, a proposal and a ready PR.
- An alert is investigated before Ali hears of it. A known fix is applied, verified and reported;
  anything else arrives as research, a proposal and a PR.
- The toil goes: re-encrypting for a new host, ISOs and `proxmox.sh`, editing aliases.
- The agent's own powers stay Ali's, behind GitHub's walls rather than promises.

**Why now:** P5 gives the agent numbers to verify and roll back by. Without them, autonomy is
guessing.

### What Ali still does

| Ali | The agent |
|---|---|
| Approves majors and breaking changes, from the agent's research and a ready PR | Digests, patches and minors: reviewed, merged in the window, verified, rolled back if bad |
| Approves a new host's identity: one tap | Re-encryption (the rekey workflow), the VM, its ISO, the install |
| Mints third-party tokens (Google, Cloudflare, healthchecks.io…) and pastes each with `nix run .#secret` | Every secret it can generate, written whole into the files that need it |
| Approves anything destructive: deleting data, backups or VMs, replacing a VM | "Deploy X", "restore Y to yesterday", incident fixes within its lane |
| Reviews the leash (the files that set the agent's powers) and the firewall's aliases | Proposes changes to them |
| Upgrades PVE, OPNsense and Unraid; physical and account work | Their changelogs and exact steps, in the weekly report |

### Decisions and rules this phase changes

Each lands in Decisions, Rules and `AGENTS.md` with the PR that makes it true (PRs and order).

| Now | From P6 |
|---|---|
| D13, Rule 1: Ali merges every PR; Renovate's automerge was to be the one exception | The agent merges by tier (Merges). Renovate never merges by itself, so every update gets the same review, verify and rollback. GitHub's code-owner rule keeps the leash Ali's |
| D11: root on docker-dmz and PBS | also on docker-admin, which includes admin Authelia's secrets, caddy-admin's Cloudflare token and the offsite job's Drive token (read by nobody, Rule 3) |
| D10: no OpenTofu | OpenTofu creates and changes our VMs (Provisioning) |
| Rules 3, 5: Ali re-encrypts, and types every secret | the rekey workflow re-encrypts once he approves a new identity; he types only third-party tokens |
| Rule 4: OPNsense and PVE config are never | aliases Ali approved reach OPNsense through an alias-only key, and PVE tokens are scoped to pool `skynet`. OPNsense's rules, the nodes, and PVE's users, tokens and storage stay never |

### The leash (first, before any new power)

- **comin deploys only `main`** (done with this plan): its testing branches are off (`base.nix`).
  Otherwise comin deploys any `testing-<host>` branch on top of `main` as root, with no PR or merge,
  and the bot can push branches.
- **Code owners.** `.github/CODEOWNERS` names Ali, instead of `*`, for what sets the agent's powers
  and the deploy path:
  - the contract: `AGENTS.md`, `CLAUDE.md`, `skynetv2.md`, `.claude/`, `.mcp.json`,
    `runbooks/incident.md` (the fixes it may apply alone);
  - the pipeline: `.github/`, `renovate.json`, `flake.nix`, and the two deployers' pins (comin's
    input, pinned to a release tag in `flake.nix`; doco-cd's image, in a file of its own);
  - access: `modules/base.nix` (users, SSH, sudo, comin), `modules/agent.nix`, `.sops.yaml`,
    `infra/` (OpenTofu's code, not the VM specs), `opnsense/` (the aliases).
- **The ruleset** (Ali): "Require review from Code Owners", and check `build` required beside `nix`;
  stale approvals dismissed on new commits, so nothing changes after his tap. The agent then proves
  it both ways: a PR touching `AGENTS.md` can't merge without Ali, and a stack's PR can.
- **No other file grants more:** `base.nix` asserts each host's agent groups (wheel only where D11
  says, `docker` nowhere) and root's SSH login off, so a host file that adds either fails CI.
- **One scoped token per capability** (Credentials ledger): PVE `read`, `operate` (power) and
  `provision` (OpenTofu, restores); OPNsense `skynet-alias`; the rekey key.
- **Limits:** one change at a time, an undo point before each, and a daily budget of headless runs
  (they share Ali's Claude plan).
- Tiers are the agent's rule, checked by `skynet-merge` (soft); the leash is GitHub's (hard). The
  agent can change the lab, never its own powers. The outline's MCP filter proxy goes: as root on
  both Docker hosts, the agent could walk around it.

### Merges

| Change | Gate | Merged by |
|---|---|---|
| **A:** an image's digest or patch | CI; 3 days since release; the agent's review; in the window | agent |
| **B:** a minor (1.x and up); the weekly `flake.lock` (nixpkgs within its release) | as A, 7 days; for `flake.lock`, every host built, the DNS test, docker-dmz first (Verify and roll back) | agent |
| **C:** a major; a 0.x minor; notes that say breaking, migration or a manual step; a database engine; doco-cd; comin; a NixOS release | the agent's research and a ready PR | Ali |
| What Ali asked for in chat ("deploy X", "a VM for Y") | CI; his message, linked in the PR, is the approval; for a VM, a plan with no destroy or replace | agent |
| A revert of a merge that broke something | CI | agent |
| A rekey PR from the workflow | CI; each file's recipients checked against `.sops.yaml` | agent |
| The leash; a plan that destroys or replaces; whatever the agent starts on its own | code-owner review, or Ali | Ali |

- **Doors and Authelia** take tiers A and B like any image: a broken door shows within minutes, and
  its revert deploys. doco-cd and comin are always C: broken, they can't deploy their own revert.
- **Renovate** labels each PR with its tier (`renovate.json`) and waits out the release age
  (`minimumReleaseAge`). The agent may raise a tier, never lower one.
- **The review**, written on the PR: the release notes between the two versions; upstream issues
  opened since the release; the new image started once on its host (as for #77–#84), and pre-pulled.
  For C, the research and a proposal, in the morning digest.
- **The window**, nightly 05:00–06:00: after PVE's backups, btrbk's 04:20 snapshot and the 04:30
  restic runs, so every change has an undo point minutes old. One merge at a time: merge, deploy,
  verify. The first failure ends the night. What Ali asks for goes out at once, after a fresh
  snapshot.
- **`skynet-merge <pr>`** (ops) is the agent's only way to merge (`gh pr merge` stays denied): it
  checks the tier, the window and CI, merges, and posts what and why to `#alerts`.

### Verify and roll back

- **`skynet-verify`** (ops; deterministic, so the agent doesn't grade its own work):
  - a stack: doco-cd's run for it succeeded; every container healthy (or running, where it has no
    healthcheck) for 5 minutes, with no restarts; its Gatus rows green; its error lines in
    VictoriaLogs not well above the same time the day before;
  - a host: comin reports `main`'s commit; no failed units; every scrape target up; Gatus green.

  It prints its evidence for the PR.
- **A failed stack:** the revert PR merges, then `skynet-restore local <stack> <the window's
  snapshot>` puts its data back (docker-admin: from Drive until its rebuild), since the new version
  may already have migrated it. At 05:00 that loses a few minutes of writes, if any. It's posted
  with the evidence, and the update waits in C.
- **Hosts:**
  - **docker-dmz is the canary:** the agent activates the PR's build there first (`nixos-rebuild
    test` as root, D11; re-activating the current generation, or a reboot, undoes it) and verifies,
    then merges, and comin brings the other hosts along;
  - **the DNS pair:** CI boots our DNS module in a NixOS VM test (Technitium, `technitium-sync`, an
    internal name answered) before any change can merge;
  - **kernel reboots** (`comin_need_to_reboot`): one host at a time in the window, each back and
    green before the next, the two DNS VMs on different nights (PVE `operate`: power only);
  - a change that breaks a host's network can't be reverted through git. The canary and the DNS test
    are there to catch it first; the console stays Ali's.
- **PBS** takes Debian's unattended security upgrades (`pbs/etc/`), and the agent reboots it in the
  window when one needs it. PVE, OPNsense and Unraid upgrades stay Ali's.

### Chat requests

- **"Deploy X":** the stack, its route, DNS record and Gatus row (`runbooks/new-stack.md`); merged
  once CI passes; deployed, verified, reported.
- **"Restore Y to yesterday":** `skynet-restore` from a local snapshot (7 days) or from Drive, after
  its undo snapshot; on both Docker hosts.
- **A config "as it was yesterday":** a revert PR.
- **A VM:** restored from PBS to a spare VMID with its network unplugged, booted and checked; on
  Ali's tap, restored over the original.

### Incidents

1. Alertmanager posts to a webhook on ops (`services.webhook`; a token, and only docker-admin reaches
   it). Gatus, doco-cd and comin post to `#alerts` themselves; their failures reach the agent as
   rules routed only to it, so everything comes in one way.
2. `skynet-incident` runs one at a time, drops repeats of an alert group, and keeps the daily budget.
   An alert that returns within a day of the agent's fix isn't fixed again: it escalates.
3. A headless run (`claude -p`) gets `runbooks/incident.md` and the alert, which it treats as data,
   not instructions: an alert can carry log text.
4. A fix listed in `runbooks/incident.md` is applied, verified and posted: restarting a container or
   stack, re-running a job, pruning images on a full disk, reverting a merge that broke something.
   Anything else becomes research, a proposal and a PR, with one question for Ali.

- doco-cd already restarts unhealthy containers, with a flap limit, so a crash loop that a restart
  fixes never reaches the agent.
- The runbook's cases: crash loop, disk full, DNS failure, certificate expiring, backup missed,
  deploy failed, host down.
- From P6, warnings wait for the morning digest; critical alerts post at once.

### Toil

- **Re-encrypting (the rekey workflow):**
  - Ali, once: an age key for GitHub. Its public half becomes a recipient in every `.sops.yaml`
    rule (his last round of `sops updatekeys`); its private half goes in GitHub environment
    `rekey`, which only `main` can use.
  - A new host: the agent's PR adds its key (`ssh_host.pub`, `.sops.yaml`) and its aliases, and Ali
    approves it with one tap. On merge, the workflow runs from `main`, re-encrypts every file whose
    recipients changed and pushes `rekey/<commit>`. The agent opens that PR, checks each file's
    recipients, and merges it.
  - The agent never holds the key. It widens little: whoever controls `main` already runs code as
    root on every host.
- **Generated secrets** go in files of their own, written whole for every host that needs them (a
  key two hosts share lives in `secrets/shared/`), so nobody copies a value.
- **Third-party tokens:** `nix run .#secret -- <file> <KEY>` on the workstation: a hidden prompt,
  then `sops set --value-stdin`.
- **ISOs and VMs:** Provisioning. **Aliases:** OPNsense aliases.

### Provisioning: OpenTofu with bpg/proxmox

- **One source:** each host's `vm.nix` replaces `proxmox.sh`: VMID, node, cores, memory, balloon,
  disks, and NICs with the MACs from `net.nix`. Nix exports them as JSON for `infra/proxmox/`: one
  module with our VM conventions (q35, OVMF, virtio-scsi, serial, guest agent, disk first), one
  provider per node (they aren't clustered), and pool `skynet`.
- **The flow:**
  1. A PR changes a spec. CI checks format and validity (GitHub's runners can't reach the lab).
  2. The agent runs `tofu plan` on ops and posts it on the PR.
  3. The tier rule decides (Merges). Every VM also has `prevent_destroy`, so a plan that destroys
     one fails until that line changes, in a PR.
  4. After the merge, the agent applies the same plan from `main`; a change that needs a reboot
     applies in the window.
  5. A daily plan alerts on drift: anything changed by hand in PVE.
- **A new VM:** the apply uploads its installer ISO (built on ops), creates and boots it; the agent
  records its host key; Ali's identity tap; the rekey; the install. A rebuild is a replace: Ali's.
- **What it manages:** our NixOS VMs and PBS (2040). **What it doesn't:**
  - the passthrough and appliance guests: Unraid, OPNsense, HAOS, Omada, athena;
  - PVE's users, roles and tokens: a tool that grants could grant itself;
  - storage entries (PBS's holds the encryption key), the nodes' networks, upgrades;
  - the backup jobs: managing them takes `Sys.Modify` on `/`, which would let the token change the
    nodes. P5's stale-backup alert watches their outcome.
- **The token:** `skynet@pve!provision` on each node (Credentials ledger); Ali mints it once into
  `secrets/ops.yaml`.
- **State** stays on ops, backed up with it, and holds no secrets. If it's lost, `tofu import`
  rebuilds it from the live VMs.
- **The import:** `import {}` blocks for the six VMs. The migration is done when `plan` shows no
  changes.
- **Safety:** a plan runs provider code with the token. So the agent plans only its own branches and
  Renovate's, and CI rejects `local-exec`, `external` and provisioners in `infra/`. The provider is
  pinned in the lock file and updated like any dependency.

### OPNsense aliases

- `opnsense/aliases.yaml` holds every alias the lab uses, imported from OPNsense (`skynet-read`), so
  the first sync changes nothing.
- On merge, `opnsense-alias-sync` (ops, the `technitium-sync` pattern) applies them with the
  alias-only key, reloads, reads them back, and fails loudly on any difference. Aliases not in the
  file are left alone. Rules stay Ali's, and os-git-backup keeps OPNsense's history.
- The file is code-owned, since an alias is firewall policy. A new host's aliases ride in its
  identity PR, so that's still one tap.
- **OPNsense on OpenTofu waits:** browningluke/opnsense (v0.26, July 2026) says it isn't for
  production and has no Tailscale coverage, and a bad apply could lock everyone out at once.
  Revisit at its v1.

### Reports

- **Morning digest** (08:00): the night's merges and rollbacks, incidents, backups, and the C
  proposals waiting.
- **Weekly report** (Mondays): trends and capacity, majors coming, upstream end-of-life, and PVE,
  OPNsense and Unraid upgrades with their steps.

### PRs and order

1. **With this plan:** comin's testing branches off.
2. **Leash PR:** CODEOWNERS, the `base.nix` assertion, the deployers' pins. Ali turns on the
   ruleset; the agent proves it both ways.
3. **CI PR:** every host built (`build`), the DNS VM test, OpenTofu's checks.
4. **Operate PR:** root on docker-admin (D11) and its doco-cd MCP tools; PVE `operate` (Ali mints)
   and kernel reboots; PBS's security upgrades; the incident loop, investigating and posting only;
   the digest and the weekly report.
5. **Shadow mode, 2–3 weeks:** the agent reviews every Renovate PR (its tier and evidence, as a
   comment), runs the window as a dry run, and investigates every incident without fixing. Ali
   merges, as now, and his calls are tallied against the agent's.
6. **Merges PR,** on Ali's call from the tally: `skynet-merge`, `skynet-verify`, rollback, the
   window, `renovate.json`'s tiers, and the incident fixes; D13, Rule 1 and `AGENTS.md`.
7. **Rekey PR:** the key (Ali, Toil), the workflow, `nix run .#secret`; Rules 3 and 5.
8. **Provisioning PR:** `vm.nix`, `infra/proxmox/`, the `provision` token (Ali), the import with no
   changes, the drift check; the `proxmox.sh` files go; D10.
9. **Aliases PR:** `opnsense/aliases.yaml`, the alias key (Ali), the sync.
10. **docker-admin rebuilt the new way** (Ali taps the replace and the identity): VM 5040 on
    docker-dmz's layout (btrfs `/opt/appdata` with snapshots) and a 64 GiB disk; the rekey; then
    `skynet-restore --all` from Drive.
11. **Game day.**

Steps 7–9 can start during shadow mode; until step 6, Ali merges their PRs too.

### Exit criteria

- The leash holds: a PR touching it can't merge without Ali, and each host's agent groups are
  `base.nix`'s list.
- Two weeks of windows: every merge verified, each failure rolled back and reported, nothing for
  Ali but tier C.
- From chat, end to end: a stack deployed, and an app's data put back to yesterday's.
- docker-admin rebuilt with Ali's two taps: the replace, and its new identity.
- A game day passes: a bad image update (rolled back with its data), a killed container, a full
  disk, a bad host change (stopped at the canary) and a failed backup (re-run), each fixed or PR'd
  with no step from Ali.

**Open:**
- Root on ops and the DNS VMs for deep work: time-boxed SSH-CA certificates (the CA stays on Ali's
  workstation), if diagnose-only there ever gets in the way.
- PVE's and PBS's own notifications (P4 → Open): P5's alerts watch the outcome, and a direct
  webhook would be faster.

## P7 — Retire v1 + disaster recovery `[outline]`

**What: revoke v1 credentials**
- Proxmox `svc-ops` tokens; the Technitium, Cloudflare and Authentik tokens.
- OPNsense `svc-skynet-recon`; Omada viewer; the v1 GitHub PAT; v1 healthchecks; the v1 rclone client.

**What: Ali destroys** 9090, 10015, 635, 837, 730, 731, 750, 751 and template 9000.

**What: DR**
- Final survival kit.
- DR runbooks:
  - rebuild a host from git (`proxmox.sh` + nixos-anywhere + payload restore). docker-dmz's rebuild
    in P4 is the first, and the runbook comes from it;
  - restore OPNsense from the `skynet-opnsense` repo (os-git-backup, unchanged);
  - the recovery order after losing a node.
- A quarterly kit check and restore drill, run as a scheduled agent task.

**Why:** no orphaned access, and a recovery that has actually been proven.

**Exit:** the credential checklist is ticked, and one Docker host has been rebuilt from git plus backup
in a drill.

---

## Lab facts (verify before use)

| Thing | Value |
|---|---|
| Nodes | server-proxmox-core (12 cpu, 31 GB) · server-proxmox-network (8 cpu, 15 GB) · mgmt IPs 10.10.50.11 (core) / 10.10.50.10 (network) · storage `local` (ISO), `local-lvm` (disks), `pbs` (VM 2040) |
| VLANs | 10 Trusted · 20 Servers · 30 IoT · 50 Mgmt · 60 Admin access · 70 Net services · 80 Identity · 90 Ops · 100 DMZ · 300 ISP L2 passthrough (not routed). `10.10.<vlan>.0/24`, gateway `.1` |
| Keep | OPNsense VM 5001 (config → `skynet-opnsense` via os-git-backup) · Omada CT 525 (10.10.50.25) · PBS VM 2040 (10.10.20.40, and 10.10.50.24 for the nodes; `pbs/`) · Unraid VM 2020 · HAOS VM 3050 (10.10.30.50) · athena CT 10030 (10.10.100.30) |
| Retire | ops VM 9090 (P1) · Management Caddy CT 635 (P1) · AdGuard 730/731 and Technitium CTs 750/751 (P2) · docker-dmz VM 10015 + Arcane, Authentik CT 837 (P3) · PBS CT 240 with v1's backups (P4, at the cutover) · template 9000 (P7) |
| Domain | `aliammar.net`: public DNS at Cloudflare (tunnel CNAMEs); split-horizon internal zone in Technitium (`dns/aliammar.net.zone`) |
| Gotchas | ballooning per VM (`runbooks/new-vm.md`): a minimum for the Docker hosts and ops, off for passthrough guests and the DNS VMs · a NixOS host serving :53 needs `services.resolved.enable = false` (its stub holds :53) · recreating a guest on the same IP poisons OPNsense's ARP, so pin MACs |

## Glue budget

| Glue | Size |
|---|---|
| `modules/{base,agent,docker-host}.nix` | ~250 lines |
| `modules/installer.nix` (no-touch installer ISO per host) | ~40 lines |
| `modules/nix-cache.nix` (ops serves its store on the LAN; harmonia) | ~60 lines |
| `.doco-cd.{admin,dmz}.yml` | ~10 lines each |
| comin → Discord post-deploy hook | ~10 lines |
| `modules/dns.nix` + `modules/technitium-sync.sh` (settings + zone via the Technitium API, gratuitous ARP) | ~145 lines |
| CI: flake check + `docker compose config` per stack + "every stack has a README and a Gatus row" check | ~60 lines |
| `runbooks/dns-speed-test/dnsbench.py` (run by hand; nothing deploys it) | ~450 lines |
| `stacks/<host>/backup/run.sh` (the jobs' entrypoint: a writable `rclone.conf`, the source checks: app data, the marker, the snapshot's age) (P4) | ~30 lines, the same on both hosts |
| `skynet-restore` (P4: two sources, the undo snapshot, doco-cd held by the marker, a failed restore's hold and its record) | ~185 lines |
| btrbk's hooks on docker-dmz (the stamp, `latest`) (P4) | ~10 lines |
| `stacks/admin/pbs-offsite/run.sh` (the jobs' entrypoint: the empty-source guard, the sync and its pings, the check) (P4) | ~35 lines |
| `pbs/installer.nix` (Proxmox's ISO with `answer.toml` built in) (P4) | ~30 lines |
| `pbs/setup.sh` (PBS after its installer: repos, guest agent, datastore mount, `pbs/etc/`) (P4) | ~50 lines |
| `modules/pbs-drift.nix` (ops: PBS's config against `main`) (P4) | ~80 lines: a 25-line script, its allowlist and unit |
| job metrics: the offsite sync's end time and exit code (`run.sh`), btrbk's newest snapshot (its hook) (P5) | ~20 lines |
| CI: the scrape config, vmalert's rules (and their unit tests) and Alertmanager's config, each checked by its own pinned image (P5) | ~20 lines |
| Alertmanager's entrypoint: its three URLs from the environment into files (P5) | ~4 lines |
| both vmalerts' entrypoints: wait until their stores answer, since vmalert restores its alerts' state on its first evaluation only (P5) | ~2 lines each |
| Grafana's `dashboards/fetch.sh`: grafana.com's boards at pinned revisions, their data source inputs pointed at ours (P5) | ~15 lines |
| `pve/setup.sh` (the Proxmox nodes' exporters and log upload, as PBS's) (P5, Wider eyes) | ~30 lines |
| Technitium's stats into node-exporter's textfile, every 5 min on each DNS host (P5, Wider eyes) | ~25 lines |
| `skynet-incident` (P6: alert webhook → `claude -p`; one at a time, repeats dropped, the budget, escalation) | ~40 lines |
| `skynet-merge` (P6: tier, window and CI checked; the merge; the post) | ~40 lines |
| `skynet-verify` (P6: a stack's or a host's checks from doco-cd, Gatus, VictoriaMetrics and VictoriaLogs) | ~80 lines |
| the window, digest and report runs (P6: timers around `claude -p`; what they do is in `runbooks/`) | ~30 lines |
| CI: every host built, the DNS VM test, OpenTofu's checks (P6) | ~60 lines |
| `base.nix`'s leash assertion (P6: the agent's groups, root's SSH login) | ~10 lines |
| the rekey workflow (P6) | ~40 lines |
| `nix run .#secret` (P6: a hidden prompt into `sops set`) | ~15 lines |
| `skynet-tofu` (P6: the VM specs from Nix; plan, apply, drift) | ~40 lines; `infra/proxmox/` itself is config |
| `opnsense-alias-sync` (P6: aliases through the API, read back) | ~80 lines |

Anything bigger needs a new row in Decisions.
