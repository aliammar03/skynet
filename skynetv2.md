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
| P4 | Backups → Google Drive | detailed (2026-10-24): restic in doco-cd jobs and PBS's datastore through rclone crypt, both to Drive; `skynet-restore` |
| P5 | Observability (agent eyes) | outline |
| P6 | Agent autonomy | outline |
| P7 | Retire v1 + disaster recovery | outline |

## Target state

```
proxmox-core (12 cpu, 31 GB)                     proxmox-network (8 cpu, 15 GB)
├ ops          VM 9091  10.10.90.91   NixOS      ├ OPNsense     VM 5001          (Ali-managed)
│   Claude Code · Discord · Remote Control       ├ Omada        CT 525           (unchanged)
├ docker-dmz   VM 10010 10.10.100.10  NixOS      ├ technitium-network VM 7050 10.10.70.50 NixOS
│   doco-cd(dmz) · caddy-apps .35 · cloudflared .33 · Authelia (apps) · apps
├ technitium-core VM 7051 10.10.70.51 NixOS      └ docker-admin VM 5040 10.10.50.40 NixOS
├ PBS CT 240 · Unraid VM 2020 · HAOS VM 3050         doco-cd(admin) · caddy-admin 10.10.60.60
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
| D8 | All alerts go to Discord `#alerts` (doco-cd via Apprise, Gatus, healthchecks.io, comin hook) | One place to look |
| D9 | Offsite = **Google Drive** via rclone with Ali's own OAuth client, scope `drive.file`, **published to production** | Drive is what Ali has; "Testing" mode tokens expire every 7 days; `drive.file` lets rclone see only what it created |
| D10 | No OpenTofu. VMs come from versioned `hosts/<h>/proxmox.sh`; internal DNS records live in `dns/aliammar.net.zone`; the Cloudflare wildcard CNAME is set once by hand | Guests change rarely |
| D11 | The agent never merges. It is **root on docker-dmz only** (passwordless sudo, every command in that host's journal), which also gives it that host's Docker socket, host key and secrets; it never prints a secret value or decrypts one on purpose. On docker-dmz's doco-cd MCP it may restart and run jobs; destroying a project or stack asks Ali each time. Everywhere else: no sudo, no Docker socket, no private age key. While it installs a host it is root on the installer, which holds the new host key that `--copy-host-keys` keeps (`runbooks/new-vm.md`); it reads only the public half | The apps host is where operate work happens, and it needs hands (Ali's call, 2026-10-24). docker-admin (admin portal, Gatus, admin secrets) and the DNS servers stay diagnose-only, so GitHub and missing credentials still leash the rest. The install window was already root-equivalent (the agent installs the OS), and it buys a one-PR install |
| D13 | `aliammar-skynet` has **Write**. The `main` ruleset requires a PR and check `nix` and blocks force-push/deletion; no review is required (Ali's call, 2026-10-21) | Branches in one repo, no approval clicks. "Never merge" is a **soft wall**: AGENTS.md + Claude Code deny rules |
| D12 | v1 archived; fresh repo; new ops VM built alongside the old one, which is then retired | Clean start without a blind spot |
| D14 | Remote access = **Tailscale**, with `os-tailscale` on OPNsense as the subnet router and split DNS for `aliammar.net`; replaces the WireGuard plan | Nothing inbound to open; it keeps working when docker-admin or a node is down, so it can reach what needs fixing |
| D15 | Backups = **restic** (run by resticprofile) in doco-cd `one_off` jobs that hold the apps stopped (`stop_services`), and PBS's datastore with **rclone** (PVE encrypts its chunks); both to Drive, nightly. PBS is rebuilt greenfield as VM 2040 from Proxmox's automated installer. Restores: `skynet-restore` | Battle-tested pieces. doco-cd already schedules jobs and is the one thing that can stop a stack without reconciliation restarting it. Cold copies need no dumps |

## Rules

1. **Every change is a PR that Ali merges.** The only planned exception is Renovate automerge of app
   digest/patch updates (P6).
2. **The system rebuilds from git.** Only payload (app data) restores from backup.
3. **Secrets are sops+age only.** Each file's recipients are Ali's master key plus the one host that
   needs it. No plaintext in git, chat or logs.
4. **The agent works in four lanes:**
   - **diagnose:** read anything except secrets;
   - **operate:** granted verbs: root on docker-dmz and its doco-cd MCP's restart and job tools
     (D11); the rest in P6;
   - **change:** via PR;
   - **never:** merge, private keys or a Docker socket outside docker-dmz, OPNsense/Unraid/PVE host
     config, deleting data.
5. **Ali handles credentials.** He mints tokens and types them via `sops`. The agent never prints a
   secret value. As root on docker-dmz it could read that host's, and doesn't.
6. **Mature tools first.** Custom glue stays inside the Glue budget.
7. **Every routed app has a health check**, and every backup job checks in to healthchecks.io.

## Repo layout (end state)

```
skynet/
├ AGENTS.md  CLAUDE.md (@AGENTS.md)  README.md  skynetv2.md
├ flake.nix  flake.lock
├ modules/            base.nix (all hosts) · agent.nix (ops) · docker-host.nix (docker-*)
├ hosts/<host>/       default.nix · net.nix · disk.nix · hardware.nix · proxmox.sh · ssh_host.pub · README.md
├ secrets/<host>.yaml host-level secrets (sops-nix)
├ dns/                aliammar.net.zone · settings.json (Technitium, P2)
├ .doco-cd.admin.yml  .doco-cd.dmz.yml
├ stacks/admin/<stack>/      (P1+)
├ stacks/dmz/<app>/          (P3+)
├ runbooks/                  new-vm · new-stack · dns-speed-test (P2); more in P6
├ .claude/settings.json  .mcp.json  .sops.yaml  renovate.json  .gitignore
└ .github/workflows/check.yml  .github/CODEOWNERS
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
- Backups (P4) copy `/opt/appdata` cold: a doco-cd job holds the stateful services stopped while
  restic runs, so databases need no dumps, and a restore is the files put back.

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
| agent (`skynet`) | root on docker-dmz (sudo, D11); doco-dmz MCP restart/job tools | that host; everywhere else diagnose-only | P3 |
| Discord bot | bot token | `#skynet` chat | P0 |
| Renovate app | repo contents/PRs | PRs (automerge P6) | P0 |
| docker-admin host key | `secrets/docker-admin.yaml`, `stacks/admin/**` | that host | P1 |
| caddy-admin / caddy-apps | Cloudflare token `Zone.DNS:Edit` on `aliammar.net` | DNS-01 | P1 / P3 |
| doco-cd API keys | REST/MCP per Docker host | held by ops (diagnose tools only until P6) | P1 / P3 |
| `#alerts` webhook | post only | Gatus, Apprise, comin, healthchecks.io | P1 |
| technitium-network / technitium-core host keys | `secrets/technitium-<node>.yaml`: Technitium `admin` password (agent-generated) | that host | P2 |
| Tailscale | Ali's account; OPNsense holds the node key | subnet routes 10.10.50.0/24, 10.10.60.60, 10.10.70.50–51 | P2 |
| docker-dmz host key, tunnel credentials | `stacks/dmz/**`, cloudflared | that host | P3 |
| rclone | Drive, scope `drive.file` (only what rclone created); Ali's own OAuth client | the backup and PBS-offsite jobs | P4 |
| restic repositories | one password per Docker host (agent-generated) | that host's snapshots | P4 |
| PBS `pve@pbs` tokens | `core`, `network`: `DatastoreBackup` on their namespace | PVE's backup jobs | P4 |
| PVE's PBS encryption keys | one per node (PVE-generated); copies in the survival kit | every backup's chunks | P4 |
| `skynet@pve` tokens | `read` = PVEAuditor on `/`, one per node (the nodes aren't clustered); `operate` = VM.PowerMgmt on pool `skynet` | Proxmox | P1 / P6 |
| OPNsense `skynet-read` | API key | Diagnostics: ARP Table · Firewall: Aliases · Firewall: Rules [new] · System: Deny config write | P1 |
| PBS / Technitium | read-only users | diagnose | P5 / P6 |

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
  restic snapshot. It is taken cold: doco-cd holds the apps stopped for the few minutes it takes.
- PBS is rebuilt greenfield: VM 2040 from Proxmox's installer, its config in git (`pbs/etc/`), with
  none of v1's leftovers.
- Every night, PBS's datastore (every guest's backups, already encrypted by PVE) is mirrored to
  Drive.
- One command restores a stack's data from any snapshot: `skynet-restore <stack> [snapshot]`.
- A failed or missed night posts to `#alerts`, and Gatus shows each job.

**Why now:** PBS already backs up every guest nightly, onto Unraid in the same house: 02:00 on the
network node, 03:30 on the core node, everything but Unraid (VM 2020) and PBS itself (CT 240).
Nothing is offsite, and app data restores only as a whole VM.

### Tools (researched 2026-10-24)

| Need | Choice | Why | Passed over |
|---|---|---|---|
| Backup engine | restic 0.19 | client-side encryption, dedup, snapshots and retention; `restore --delete` puts a folder back exactly; its `rclone:` backend reaches Drive | Kopia (younger), Borg (no Drive), Duplicati (database corruption history), tarball tools such as offen/docker-volume-backup (no dedup: a full upload every night) |
| Runner | resticprofile 0.33; its image ships restic, rclone and curl | one profile file in git holds backup, retention, check and the healthchecks.io pings (`send-before` / `send-after` / `send-after-fail`). Restores and every other restic command run through it | Backrest and NixOS `services.restic` (their schedulers can't hold doco-cd's stacks stopped), autorestic |
| Schedule and quiet window | doco-cd `one_off` jobs with `cd.doco.job.stop_services` | doco-cd stops the listed services and waits; it runs the job, then starts them again after success or failure. The gap isn't drift, so reconciliation leaves it alone. Cold files are consistent: no database dumps, and no per-app import on restore | stopping by hand (reconciliation restarts it); `docker pause` (fails healthchecks, then reconciliation restarts it); per-app dumps |
| Drive | rclone with Ali's own OAuth client, scope `drive.file` (D9) | rclone sees only the files it created. rclone's shared client stops working during 2026 | a service account (no storage on a personal Drive) |
| PBS offsite | `rclone sync` of the datastore | chunks are immutable files, so each night sends only new ones. PVE already encrypts them client-side; only guest IDs and dates show. Drive keeps deleted files in the trash for 30 days | a second PBS (remote sync); PBS 4's S3 datastores (Drive isn't S3); restic over the datastore (re-deduplicating PBS's chunks); an rclone `crypt` layer (a second key for nothing) |
| PBS itself | a fresh VM from Proxmox's automated installer (`proxmox-auto-install-assistant`, answer file in git) | the official appliance and upgrade path, installed no-touch like the NixOS hosts | PBS on NixOS (shelved, Open); cleaning CT 240 in place (it keeps v1's users and history) |

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
  - v1's leftovers: 15 groups of retired or vanished guests (203 snapshots; Ali prunes them), user
    `svc-ops@pbs`, and PBS backing itself up.
- **Drive** (Ali): free space of at least twice datastore plus app data (about 0.3 TB now).
- **The uplink:** datastore size ÷ upload speed is the first sync's length (Drive's own pace is
  about 2 files a second, so 135k chunks take about 19 hours).
- **Unraid** (Ali): the share's NFS export opened to VM 2040 (read-write) and docker-admin
  (read-only).
- **Egress:** both Docker hosts reach Google's APIs on :443 (rule 810).

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

One stack per Docker host: three doco-cd `one_off` jobs on the pinned resticprofile image, all
reading `profiles.yaml` from git.
- **`backup`**, nightly at 04:30, after the guests' PBS backups:
  - `stop_services` (below) holds the host's stateful services stopped;
  - then `resticprofile backup`, with retention right after it;
  - repository `rclone:gdrive:skynet/restic/<host>`, source `/opt/appdata`, 64 MiB packs;
  - keeps 7 daily, 4 weekly and 12 monthly snapshots.
- **`check`**, Sundays: `restic check --read-data-subset 5%`, with nothing stopped.
- **`restore`**, run only by `skynet-restore`: the same `stop_services`, then
  `restic restore <snapshot> --target / --include /opt/appdata/<stack> --delete`.

**Stopped during `backup` and `restore`.** These are compose service names, the stacks whose
READMEs class their data as `data`:
- docker-dmz: `authelia/authelia`, `obsidian/obsidian`, `karakeep/karakeep`, `paperless/paperless`,
  `calibre/calibre`, `sillytavern/sillytavern`, `marinara/marinara`, `jikan/jikan`, `jikan/mongo`,
  `aiometadata/aiometadata`, `aiostreams/aiostreams`, `librespeed/librespeed`;
- docker-admin: `authelia/authelia`, `gatus/gatus`.

**Not backed up**, because these are class `cache` and rebuild themselves:
- `aiometadata/poster-cache` and `aiometadata/redis`;
- `jikan/redis` and `jikan/typesense`;
- `karakeep/meili`;
- the doors' certificates.

**Files:**
- `compose.yaml` and `profiles.yaml`;
- `secret.sops.env`: `RESTIC_PASSWORD` (agent-generated) and `HC_PING_URL`;
- `rclone.sops.conf` (Ali's).

**Mounts:** `/opt/appdata`, read-write because restores write. The job copies `rclone.conf`
somewhere writable at start, since rclone saves refreshed tokens.

**Notes:**
- The first night uploads everything (docker-dmz has about 7 GB), so the apps stay stopped longer
  that once.
- To verify while building: a job scheduled `0 0 30 2 *` (there is no 30 February) must never fire
  yet still run on `POST /v1/api/job/restore/run`. If not, the restore runs from `skynet-restore`
  with doco-cd's reconciliation off for its minutes.

### Restores: `skynet-restore` (glue on both Docker hosts, from `modules/docker-host.nix`)

- `skynet-restore <stack> [snapshot]` (default `latest`) does three things:
  - writes the request to `/opt/appdata/backup/restore.request`;
  - triggers the `restore` job through doco-cd's API (`/v1/api/job/restore/run?stack=backup`) and
    waits;
  - prints the result.

  doco-cd stops the stateful services, restic puts `/opt/appdata/<stack>` back exactly as in the
  snapshot, and doco-cd starts the services again.
- `skynet-restore --list [stack]`: the snapshots, and what changed between them.
- `skynet-restore <stack> [snapshot] --to <dir>`: into a scratch folder, with nothing stopped (for
  drills, or to fetch one file).
- `skynet-restore --all [snapshot]`: every stack, for a rebuilt host (P7).
- It runs as root on the host: `ssh -t <you>@<host> sudo skynet-restore …`. On docker-dmz the agent
  can run it too (D11).
- A restore stops every stateful service on its host for those minutes, not just the one stack:
  one job, one stop list.

### PBS, greenfield: VM 2040 (`pbs/`)

CT 240 carries v1: its users, its retired guests' history, and PBS backing itself up. A new PBS
starts clean beside it, with its config in git from the first day. CT 240 retires once the new one
has proved itself.
- **VM 2040** on the core node, at 10.10.20.40 (VLAN 20), CT 240's address, so `HOST_PBS`, its
  firewall rules and the Gatus row carry over: 2 vCPU, 4 GB with 2 GB guaranteed
  (ballooning: verify, GC and backups use the rest), and a 32 GB OS disk on `local-lvm`. `pbs/proxmox.sh` is the `qm create`, as for
  the NixOS hosts.
- **Install:** Proxmox's automated installer. `pbs/answer.toml` holds:
  - the disk, address and hostname;
  - root's SSH keys (the agent's and Ali's);
  - the hash of a random root password (agent-generated; the password goes to sops for Ali).

  The agent builds the ISO on CT 240 (`proxmox-auto-install-assistant prepare-iso`), and Ali boots
  the VM from it.
- **Datastore `skynet`:** a new folder in the same Unraid share (`/mnt/user/pbs-backups/skynet`),
  with namespaces `core` and `network`.
- **Config from git** (`pbs/etc/`, below):
  - prune per namespace, keeping 14 daily, 8 weekly and 12 monthly, as now;
  - verify daily (verified snapshots skipped, re-verified after 30 days);
  - GC on Sundays at 12:00, after the offsite run.
- **Users:**
  - `root@pam` (the agent over SSH, D11);
  - `pve@pbs`, with tokens `core` and `network`, each `DatastoreBackup` on its own namespace.

  Nothing else.
- **Cutover** (Ali, PVE config), on each node:
  - add storage `pbs`: the new server, its token, and a new client-side encryption key (PVE
    generates it; it goes in the survival kit);
  - point the backup job at it, leaving out the retired guests until P7 destroys them (core: 10015,
    9000, 9090, 731, 751; network: 635, 730, 750, 837).

  The first night writes full backups into the new datastore.
- **Freeing .40 first** (Ali, PVE config): CT 240 moves to 10.10.20.39 (`pct set 240 --net0 …` with
  the new IP, then a restart), and PVE's `pbs-unraid` storage entries follow it. Then VM 2040
  installs at .40.
- **CT 240** stays at .39 for 30 days, its jobs off, as the fallback with the history. Then P7
  removes it and the `unraid` datastore (Ali); VM 2040 replaces it for good.

### PBS offsite: `stacks/admin/pbs-offsite/` (docker-admin)

- **Mount** (docker-admin's Nix config): the datastore folder (`/mnt/user/pbs-backups/skynet`) over
  NFS, read-only and automounted, at `/mnt/pbs-datastore`.
- **Job** (`one_off`, daily at 06:00): after both nodes' backups and the prune, and outside GC
  (Sundays 12:00) and verify.
  - It runs `rclone sync /mnt/pbs-datastore gdrive:skynet/pbs`. The chunks are already encrypted, by
    PVE's keys.
  - Flags: `--transfers 4 --tpslimit 8 --drive-chunk-size 64M --max-transfer 700G --cutoff-mode soft`.
  - It leaves out the datastore's lock and GC-status files.
- **Weekly:** `rclone check --one-way` against the datastore.
- **A guest from Drive** (site loss, or the drill): copy the datastore back into a scratch
  datastore (`rclone copy gdrive:skynet/pbs <dir>`), verify it on PBS, then restore the guest from
  PVE with its node's key. Try `rclone mount` with `--vfs-cache-mode full` first: it fetches only
  the chunks the restore reads.

### PBS's config in git: `pbs/etc/`

PBS stays Proxmox's appliance (VM 2040, Debian), but its settings live in git, the way OPNsense's do
(os-git-backup to `skynet-opnsense`).
- **`pbs/etc/`:** copies of `/etc/proxmox-backup`'s config files, from an allowlist: `datastore.cfg`,
  `prune.cfg`, `verification.cfg`, `sync.cfg`, `acl.cfg`, `user.cfg`, `domains.cfg`, `node.cfg`,
  `notifications.cfg` and `traffic-control.cfg` (the agent checks the list against the live
  folder). Never the secrets: `shadow.json`, `token.shadow`, `tfa.json`, keys and certificates,
  `*-priv.cfg`, and `remote.cfg`, which holds passwords.
- **Changes:** a change on PBS, whether the agent's (root, D11) or one in its UI, is followed by its
  PR (rule 2).
- **Drift:** a nightly timer on ops copies the allowlisted files from PBS over SSH and compares them
  with `main`'s. A difference goes to `#alerts`, naming the files.
- **Rebuild:**
  - a fresh PBS from `pbs/answer.toml`, with these files copied back;
  - the datastore re-added from its Unraid folder, as-is;
  - PVE's backup credentials re-created;
  - PVE's storage entry takes the new fingerprint (Ali).

### Monitoring

- **healthchecks.io:** Ali creates three checks, each daily: `backup docker-dmz` and
  `backup docker-admin` (grace 3 h), and `pbs-offsite` (grace 6 h). Their ping URLs go into the
  stacks' secrets, and their badge URLs into Gatus's. resticprofile pings start, success and
  failure; the rclone job pings with curl.
- **Gatus:** one job row per check from its badge, as for the heartbeats.
- **`#alerts`:** `notify_on: failure` on every job.

### Survival kit (Ali, outside the lab)

- the restic passwords, one per host;
- PVE's PBS encryption keys, one per node (Datacenter → Storage → `pbs` → Encryption: download).
  Without them every copy, on Unraid or on Drive, is unreadable;
- the OAuth client's ID and secret (logging in again gives a new token);
- PBS's root password;
- the age master key.

Copy them with `nix shell nixpkgs#sops -c sops -d <file>` on the workstation, into the password
manager.

### PRs and order

1. **Ali:**
   - the Prechecks' answers;
   - Drive access;
   - the three healthchecks.io checks.
2. **PBS greenfield PR:**
   - `pbs/`: `proxmox.sh`, `answer.toml`, `etc/` and a README; ops' drift timer;
   - the agent builds the ISO on CT 240, and Ali creates VM 2040 from it;
   - Ali does the cutover on both nodes, and stores the new encryption keys in the survival kit.

   The first night fills the new datastore.
3. **App backups PR:**
   - both `backup` stacks, `skynet-restore` and the Gatus rows;
   - the restic passwords, agent-generated;
   - Ali adds `rclone.sops.conf` and the healthchecks.io URLs on the branch.

   The first night runs long.
4. **Drill:** `skynet-restore librespeed` in place, and karakeep `--to` a scratch folder. Evidence
   goes in the PR.
5. **PBS offsite PR:**
   - the NFS mount and `pbs-offsite`;
   - Ali: the Unraid export, and an OPNsense rule for docker-admin → Unraid NFS (2049).

   The first sync may take days.
6. **Drill:** one small guest restored from the Drive copy.

### Exit criteria

- Seven green nights in a row, for all three jobs and for VM 2040's backups. CT 240's jobs are off.
- Both drills done, with evidence in their PRs.
- Ali confirms the survival kit is stored.
- `pbs/etc/` matches PBS, and the drift check is quiet.
- `runbooks/restore.md` covers five cases: an app, a host, a guest, PBS rebuilt from `pbs/etc/`, and
  a restore from Drive with nothing else left.

**Open:**
- Whether any Unraid shares need offsite too (not part of this phase).
- PBS as a NixOS VM: shelved (Ali, 2026-10-24); its config goes to git meanwhile (`pbs/etc/`). nixpkgs has only the client. A community package and
  module (nixos-pbs, PBS 4.2.3, from source in an FHS wrapper) has had a few testers since
  2026-06, with its nixpkgs PR open. Once it lands, trial it beside the current PBS: a sync job
  into its own datastore, verify, a restore drill. Move only when that holds, by pointing it at
  the existing Unraid datastore; PVE's storage entry then changes (Ali).

## P5 — Observability `[outline]`

**What** (all on docker-admin)
- **VictoriaMetrics** scrapes:
  - node-exporter on the NixOS hosts and container metrics;
  - pve-exporter (`skynet@pve!read`) and PBS;
  - comin (:4243), doco-cd (:9120) and Gatus.
- **VictoriaLogs:** hosts ship journald via `systemd-journal-upload`. Docker logs are already in
  journald.
- **Grafana:** an Authelia OIDC client, with dashboards provisioned from git.
- **Alerting:** vmalert → Alertmanager → Discord for disk, memory, backup age and cert expiry.
- **Homepage** dashboard.
- **Sizing:** grow docker-admin to 6 GB once Authentik is gone.
- **Agent eyes:** ops `.mcp.json` gets `mcp-victoriametrics` and `mcp-victorialogs`.

**Why:** the agent diagnoses from live metrics and logs. This replaces v1's collectors and renderers.

**Exit**
- The agent answers "why is X slow?" and "what happened at 03:00?" from data.
- A disk-fill test alerts.

**Open:** retention vs disk; exporters for OPNsense and Omada.

## P6 — Agent autonomy `[outline]`

**What: the operate lane**
- Already granted in P3 (D11): root on docker-dmz, and docker-dmz's doco-cd MCP tools
  (`control_project`, `control_stack`, `trigger_scheduled_job`, `compact_mirrors`; destroy and
  remove ask Ali). P6 decides the rest.
- doco-cd MCP: `control_project` (restart/start/stop) and `trigger_scheduled_job`, for docker-admin.
- Proxmox `skynet@pve!operate`: a custom role with `VM.PowerMgmt` on pool `skynet` (5040, 10010).
- SSH as `svc-ops` on the Docker hosts, with Nix-declared sudo for `systemctl restart docker` and
  `journalctl`.
- Time-boxed SSH-CA root grants for deep work (the CA stays on Ali's workstation).
- Optional hard wall: a ~40-line MCP filter proxy in front of doco-cd, so destructive tools are
  impossible rather than just denied.

**What: the alert loop**
1. Gatus, Alertmanager or doco-cd fires.
2. `services.webhook` on ops (LAN-only, token-protected) receives it.
3. `claude -p` investigates using the runbooks and posts findings to `#alerts`.
4. It then applies an operate fix or opens a PR.

**What: runbooks** for crashloop, disk-full, dns-failure, cert-expired, backup-missed and
deploy-failed (which leads to a revert PR).

**What: Renovate automerge**
- Scope: digests and patches under `stacks/dmz/**`.
- Gates: `minimumReleaseAge: 3 days`, green CI.
- CODEOWNERS keeps `hosts/`, `modules/`, `stacks/admin/`, `.github/`, `.claude/` and `AGENTS.md`
  Ali-reviewed.

**What: weekly report.** A "State of the Lab" written by `claude -p` from metrics, posted to Discord.

**Why:** hands-off operation. The agent fixes what's safe and proposes the rest.

**Exit:** a game day passes. A bad env var, a killed container, a full disk and a failed image update
are each fixed or PR'd, with no human step except merges.

**Open:** which operate verbs ship on day one (start with restart/reconcile; add reboots later).

## P7 — Retire v1 + disaster recovery `[outline]`

**What: revoke v1 credentials**
- Proxmox `svc-ops` tokens; the Technitium, Cloudflare and Authentik tokens.
- OPNsense `svc-skynet-recon`; Omada viewer; the v1 GitHub PAT; v1 healthchecks; the v1 rclone client.

**What: Ali destroys** 9090, 10015, 635, 837, 730, 731, 750, 751 and template 9000.

**What: DR**
- Final survival kit.
- DR runbooks:
  - rebuild a host from git (`proxmox.sh` + nixos-anywhere + payload restore);
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
| Nodes | server-proxmox-core (12 cpu, 31 GB) · server-proxmox-network (8 cpu, 15 GB) · mgmt IPs 10.10.50.11 (core) / 10.10.50.10 (network) · storage `local` (ISO), `local-lvm` (disks), `pbs-unraid` |
| VLANs | 10 Trusted · 20 Servers · 30 IoT · 50 Mgmt · 60 Admin access · 70 Net services · 80 Identity · 90 Ops · 100 DMZ · 300 ISP L2 passthrough (not routed). `10.10.<vlan>.0/24`, gateway `.1` |
| Keep | OPNsense VM 5001 (config → `skynet-opnsense` via os-git-backup) · Omada CT 525 (10.10.50.25) · PBS CT 240 (10.10.20.40; starts after Unraid NFS; P4 replaces it with VM 2040) · Unraid VM 2020 · HAOS VM 3050 (10.10.30.50) · athena CT 10030 (10.10.100.30) |
| Retire | ops VM 9090 (P1) · Management Caddy CT 635 (P1) · AdGuard 730/731 and Technitium CTs 750/751 (P2) · docker-dmz VM 10015 + Arcane, Authentik CT 837 (P3) · template 9000 (P7) |
| Domain | `aliammar.net`: public DNS at Cloudflare (tunnel CNAMEs); split-horizon internal zone in Technitium (`dns/aliammar.net.zone`) |
| Gotchas | turn off ballooning on VMs · a NixOS host serving :53 needs `services.resolved.enable = false` (its stub holds :53) · recreating a guest on the same IP poisons OPNsense's ARP, so pin MACs |

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
| `stacks/<host>/backup/` job entrypoint (a writable `rclone.conf`, the restore request) (P4) | ~30 lines |
| `skynet-restore` (P4) | ~60 lines |
| `stacks/admin/pbs-offsite/` job script (P4) | ~20 lines |
| ops: PBS config drift check (P4) | ~30 lines |
| alert webhook → `claude -p` (P6) | ~40 lines |
| doco-cd MCP filter proxy (P6, optional) | ~40 lines |

Anything bigger needs a new row in Decisions.
