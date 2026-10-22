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
| P0 | Foundations + new ops VM | in progress — steps 1–12 done |
| P1 | docker-admin: admin door, identity, status | in progress — docker-admin installed; doco-cd |
| P2 | DNS (Technitium only) + remote access | outline |
| P3 | docker-dmz: apps + public path | outline |
| P4 | Backups → Google Drive | outline |
| P5 | Observability (agent eyes) | outline |
| P6 | Agent autonomy | outline |
| P7 | Retire v1 + disaster recovery | outline |

## Target state

```
proxmox-core (12 cpu, 31 GB)                     proxmox-network (8 cpu, 15 GB)
├ ops          VM 9091  10.10.90.91   NixOS      ├ OPNsense     VM 5001          (Ali-managed)
│   Claude Code · Discord · Remote Control       ├ Omada        CT 525           (unchanged)
├ docker-dmz   VM 10010 10.10.100.10  NixOS      ├ technitium   CT 750 .70.50    (primary)
│   doco-cd(dmz) · caddy-apps .35 · cloudflared .33 · apps
├ technitium   CT 751 10.10.70.51 (secondary)    └ docker-admin VM 5040 10.10.50.40 NixOS
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
| D4 | **Authelia**, with an auth mode per app: `own` / `oidc` / `forward` | Config lives in git; ~50 MB; OIDC + forward-auth + passkeys |
| D5 | **Technitium** is the only DNS (750 primary, 751 secondary) and does ad-blocking; AdGuard retired | One product; a wildcard record means no per-app DNS work |
| D6 | Two Docker hosts: **docker-dmz** (apps, core node), **docker-admin** (admin, identity, monitoring; network node) | Segmentation; monitoring survives losing the core node |
| D7 | Agent = **Claude Code** on the ops VM; chat via **Discord** (Channels) + the Claude app (Remote Control) | Telegram is blocked; no custom UI to build |
| D8 | All alerts go to Discord `#alerts` (doco-cd via Apprise, Gatus, healthchecks.io, comin hook) | One place to look |
| D9 | Offsite = **Google Drive** via rclone with Ali's own OAuth client, **published to production** | Drive is what Ali has; "Testing" mode tokens expire every 7 days |
| D10 | No OpenTofu. VMs come from versioned `hosts/<h>/proxmox.sh`; DNS records as decided in P2; the Cloudflare wildcard CNAME is set once by hand | Guests change rarely |
| D11 | The agent never merges, never holds a private age key, never gets a Docker socket | GitHub and missing credentials enforce the leash |
| D13 | `aliammar-skynet` has **Write**. The `main` ruleset requires a PR and check `nix` and blocks force-push/deletion; no review is required (Ali's call, 2026-10-21) | Branches in one repo, no approval clicks. "Never merge" is a **soft wall**: AGENTS.md + Claude Code deny rules |
| D12 | v1 archived; fresh repo; new ops VM built alongside the old one, which is then retired | Clean start without a blind spot |

## Rules

1. **Every change is a PR that Ali merges.** The only planned exception is Renovate automerge of app
   digest/patch updates (P6).
2. **The system rebuilds from git.** Only payload (app data) restores from backup.
3. **Secrets are sops+age only.** Each file's recipients are Ali's master key plus the one host that
   needs it. No plaintext in git, chat or logs.
4. **The agent works in four lanes:**
   - **diagnose:** read anything except secrets;
   - **operate:** granted, reversible verbs (P6);
   - **change:** via PR;
   - **never:** merge, private keys, Docker socket, OPNsense/Unraid/PVE host config, deleting data.
5. **Ali handles credentials.** He mints tokens and types them via `sops`. The agent never sees a
   secret value.
6. **Mature tools first.** Custom glue stays inside the Glue budget.
7. **Every routed app has a health check**, and every backup job checks in to healthchecks.io.

## Repo layout (end state)

```
skynet/
├ AGENTS.md  CLAUDE.md (@AGENTS.md)  README.md  skynetv2.md
├ flake.nix  flake.lock
├ modules/            base.nix (all hosts) · agent.nix (ops) · docker-host.nix (docker-*)
├ hosts/<host>/       default.nix · disk.nix · hardware.nix · proxmox.sh · README.md
├ secrets/<host>.yaml host-level secrets (sops-nix)
├ .doco-cd.admin.yml  .doco-cd.dmz.yml
├ stacks/admin/<stack>/      (P1+)
├ stacks/dmz/<app>/          (P3+)
├ runbooks/                  (P6)
├ .claude/settings.json  .mcp.json  .sops.yaml  renovate.json  .gitignore
└ .github/workflows/check.yml  .github/CODEOWNERS
```

## Conventions

### Stack folder `stacks/<host>/<name>/`

| File | When | Content |
|---|---|---|
| `compose.yaml` | always | images pinned `tag@sha256:…`; a healthcheck; `restart: unless-stopped`; network `edge` (doors also join their macvlan) |
| `secret.sops.env` | has secrets | dotenv, sops-encrypted for that host only; used via `env_file` |
| `caddy.conf` | routed | `@x host x.aliammar.net` + `handle @x { [import authelia] reverse_proxy <container>:<port> }` |
| `gatus.yaml` | routed | an `endpoints:` list for this app only |
| `README.md` | always | purpose · URL · auth mode · data paths + backup class · secret key *names* · upstream link · gotchas |

**Routing**
- Each door has **one wildcard site** `*.aliammar.net`. It imports the app snippets and ends with a
  catch-all `404`.
- The wildcard cert comes via Cloudflare DNS-01, so individual names never appear in certificate
  transparency logs.
- A door mounts each `caddy.conf` and `gatus.yaml` as a **single-file bind mount, never the folder**.
  doco-cd writes decrypted secrets into that folder.

**Auth modes**
- **`own`** (default): a plain proxy; the app has its own login.
- **`oidc`:** the client goes in `stacks/admin/authelia/oidc-clients.yml`. That single file holds
  the whole list, because Authelia replaces a repeated key rather than appending to it. The app's
  secret lives in its `secret.sops.env`.
- **`forward`:** add `import authelia` to the app's `caddy.conf`.

**Data**
- Bind mounts go at `/opt/appdata/<app>/<role>`. Named volumes are only for DB engines.
- DB dumps land in `/opt/appdata`, which restic backs up.

**Networks**
- Networks are created by the host's Nix config, not by stacks:
  - `edge`: a bridge shared by apps and doors;
  - a macvlan for the doors (`dmz`, `adm60`).
- Apps get no LAN IP. Doors reach them by container name.

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
| Discord bot | bot token | `#skynet` chat | P0 |
| Renovate app | repo contents/PRs | PRs (automerge P6) | P0 |
| docker-admin host key | `secrets/docker-admin.yaml`, `stacks/admin/**` | that host | P1 |
| caddy-admin / caddy-apps | Cloudflare token `Zone.DNS:Edit` on `aliammar.net` | DNS-01 | P1 / P3 |
| doco-cd API keys | REST/MCP per Docker host | held by ops (diagnose tools only until P6) | P1 / P3 |
| `#alerts` webhook | post only | Gatus, Apprise, comin, healthchecks.io | P1 |
| docker-dmz host key, tunnel credentials | `stacks/dmz/**`, cloudflared | that host | P3 |
| rclone | Drive scope, Ali's own OAuth client | backup jobs | P4 |
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
- **Docker:** `virtualisation.docker` with log-driver `journald` and weekly autoPrune.
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
- **Files:** `conf/` (mounted at `/etc/caddy`, no secrets): `Caddyfile`, `sites/<name>.conf`, `certs/`
  (upstream certs, public). Beside it: `secret.sops.env` (`CLOUDFLARE_API_TOKEN`).
- **Caddyfile:**
  - global (no `email`: Let's Encrypt no longer sends expiry mail): `acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}`, `servers { protocols h1 h2 }`;
  - snippet: `(authelia) { forward_auth authelia:9091 { uri /api/authz/forward-auth; copy_headers Remote-User Remote-Groups Remote-Email Remote-Name } }`;
  - site: `*.aliammar.net { import /etc/caddy/sites/*.conf; handle { respond 404 } }`.

**`authelia`**
- **Container:** image `ghcr.io/authelia/authelia`; on `edge` only (P3 publishes `10.10.50.40:9091`
  for caddy-apps); data (sqlite, `notification.txt`) in `/opt/appdata/authelia`.
- **Files:** `configuration.yml` (plaintext, no secrets); `secret.sops.env` (`AUTHELIA_SESSION_SECRET`,
  `AUTHELIA_STORAGE_ENCRYPTION_KEY`, `AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET`,
  agent-generated); `users.sops.yml` (Ali: argon2 hash). P3 adds `oidc-clients.yml` as a second
  `--config`.
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
  - doco-cd isn't checked here (its API answers only to ops); heartbeat is a doco-cd job, so a
    dead doco-cd pages via healthchecks.io.
- From P3, one single-file mount per app `gatus.yaml`.

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
| opnsense | https://10.10.50.1 | `tls_server_name OPNsense.internal` + trust its cert (`tls_trust_pool file`). In OPNsense, System → Settings → Administration → **Alternate Hostnames** must include `opnsense.aliammar.net` |
| proxmox-core / proxmox-network | https://10.10.50.11:8006 / .10:8006 | trust each node's `pve-root-ca.pem` |
| pbs | https://10.10.20.40:8007 | trust its self-signed cert |
| technitium-core / technitium-network | http://10.10.70.51:5380 / .50:5380 | CT 751 / CT 750 |
| omada | https://10.10.50.25:8043 | pin its self-signed cert, `tls_server_name Omada` |
| unraid | http://10.10.20.20 | `header_down Location ^http:// https://` (it redirects to absolute http URLs) |
| auth | authelia:9091 | portal; moves to the apps door in P3 |
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
3. Point the admin names → 10.10.60.60 in Technitium. Test every site by name from an admin client.
   `pct shutdown 635`, set `onboot 0`, and remove 10.10.60.35 from `HOST_PROXY_ADMIN`.
4. Ali enrolls in Authelia:
   - (done with the authelia PR: an argon2 hash in `users.sops.yml` via `sops`);
   - point `auth` → 10.10.60.60 (done) (it was Authentik's, 10.10.100.35);
   - log in and register a passkey (the code is in `/opt/appdata/authelia/notification.txt`);
   - then `import authelia` per site (done).

   Direct IPs remain the break-glass path.
5. Retire v1 monitoring:
   - disable `skynet-watch` on 9090 and shut 9090 down (`onboot 0`);
   - remove 10.10.90.90 from `HOST_SKYNET_OPS`.

   CT 635 and VM 9090 stay stopped for 14 days, then Ali destroys them (P7).

### Exit criteria

- Every admin name loads with a valid cert behind an Authelia passkey. Direct IPs still work.
- Gatus is all green. A stopped test container alerts in `#alerts`, and so does its recovery.
- doco-cd deploys and failed comin deploys post to `#alerts`. The healthchecks.io heartbeat is green.
- The agent lists docker-admin projects and runs via MCP, and answers "is X up?" from Gatus.
- CT 635 and VM 9090 are off. Renovate tracks every pinned image (compose + Nix).

---

## P2 — DNS + remote access `[outline]`

**What**
- Technitium is the only resolver.
  - 750 (network, .50) is primary for `aliammar.net`; 751 (core, .51) is secondary (zone transfer + NOTIFY).
  - A wildcard `*.aliammar.net` A → 10.10.100.35 (apps door, live in P3). Explicit admin names →
    10.10.60.60.
  - Records are kept in git and applied via the Technitium API or UI. **Decide here** which method
    round-trips cleanly (zone file import vs API script).
  - Ad-blocking via Technitium block lists. Server settings are Ali-applied and documented in
    `hosts/technitium/README.md`.
- OPNsense:
  - DHCP hands out .51/.50 on every VLAN;
  - `ROLE_DNS_RESOLVERS` drops AdGuard; the "block other DNS" rules stay.
- Retire AdGuard CTs 730/731.
- WireGuard road-warrior on OPNsense (if not already set up), using Technitium for DNS and admin-client
  rights.

**Why:** one DNS product; the wildcard ends per-app DNS work; remote admin without exposing anything.

**Exit**
- Every VLAN resolves via Technitium, and ads are blocked.
- A phone on WireGuard opens `opnsense.aliammar.net`.
- AdGuard is stopped.

**Open:** the record-management method; the secondary's sync settings.

## P3 — docker-dmz: apps + public path `[outline]`

**What: the host.** New VM 10010:
- 10.10.100.10 on the core node; NixOS with `docker-host.nix`;
- target `dmz` (`.doco-cd.dmz.yml`);
- NIC `dmz` on VLAN 100, carrying the host IP and the macvlan.

**What: the doors.**
- **`caddy-apps`:**
  - macvlan 10.10.100.35;
  - a wildcard site importing each app's `caddy.conf` (single-file mounts);
  - its `authelia` snippet points at 10.10.50.40:9091;
  - it serves `auth.aliammar.net`.
- **`cloudflared`:**
  - macvlan .33;
  - explicit hostname ingress, then a 404 catch-all;
  - DNS 1.1.1.1/8.8.8.8 (Technitium returns empty for the `_v2-origintunneld` SRV record).
- **Cloudflare:** Ali sets the `*.aliammar.net` CNAME → tunnel once.

**What: migration.** The doors cut over first: they take .35/.33 and proxy to the old backends. Then
apps move one at a time, in this order: librespeed, silly, calibre (forward), karakeep,
paperless-ngx, obsidian-livesync (couchdb), aiostreams, aiometadata (mongo, jikan, redis, typesense),
marinara. For each app:
1. Ali re-encrypts its secrets for docker-dmz (`sops -d` the v1 file with the old key, then `sops`
   the new file).
2. Stop the old app; rsync `/opt/docker/appdata/<svc>` → `/opt/appdata/<app>`.
3. Deploy, flip its route, confirm Gatus is green.
4. Add a tunnel hostname if the app is public.

**Why:** apps come under GitOps on a host rebuilt from git. This retires Arcane, the Ubuntu VM and
Authentik.

**Carry-over gotchas**
- HTTP/3 off (`protocols h1 h2`) for Obsidian LiveSync.
- couchdb data ownership.
- Pin meilisearch and typesense versions.
- Firewall: caddy-apps → 10.10.50.40:9091.

**Exit**
- Every app is green in Gatus, internally and publicly where listed.
- The old VM 10015, Authentik CT 837 and Arcane are stopped. Ali destroys them in P7.

**Open:** reuse the v1 tunnel or create a new one; how to lay out the aiometadata stack.

## P4 — Backups → Google Drive `[outline]`

**What: Drive access.** Ali creates a Google Cloud project and an OAuth "Desktop" client, with the
consent screen **published to production**. He runs `rclone config` on the workstation, and
`rclone.conf` goes into sops for each Docker host that needs it.

**What: app data.** `stacks/<host>/backup/` holds doco-cd scheduled jobs:
- DB dumps into `/opt/appdata/<app>/dump`;
- restic → `rclone:gdrive:skynet/restic-<host>`, keeping 7 daily / 4 weekly / 6 monthly;
- a weekly `restic check --read-data-subset=5%`.

**What: PBS offsite.** PBS stays, with its local datastore on Unraid. `stacks/admin/pbs-offsite`
mounts the datastore read-only over NFS and runs `rclone sync` → `gdrive:skynet/pbs`:
- after the backup window and never during garbage collection;
- with a weekly `rclone check`.

**What: proof.** Every job pings healthchecks.io (start / success / fail). The survival kit gets the
restic password, the PBS encryption key and the rclone client details.

**Why:** an offsite payload copy on storage Ali already has, defined in git.

**Note:** Drive allows about 750 GB/day upload and creates files slowly, so the first PBS sync may
take days. restic's pack files keep the file count low.

**Exit**
- 7 consecutive green nights.
- A restore drill: one app from Drive into a scratch folder, plus one PBS guest restore. Evidence goes
  in the phase PR.

**Open:** retention; whether any Unraid shares also need offsite.

## P5 — Observability `[outline]`

**What** (all on docker-admin)
- **VictoriaMetrics** scrapes:
  - node-exporter on the NixOS hosts and container metrics;
  - pve-exporter (`skynet@pve!read`) and PBS;
  - comin (:4243), doco-cd (:9120) and Gatus.
- **VictoriaLogs:** hosts ship journald via `systemd-journal-upload`. Docker logs are already in
  journald.
- **Grafana:** the first Authelia OIDC client, with dashboards provisioned from git.
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
- doco-cd MCP: `control_project` (restart/start/stop) and `trigger_scheduled_job`.
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

**What: Ali destroys** 9090, 10015, 635, 837, 730, 731 and template 9000.

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
| Keep | OPNsense VM 5001 (config → `skynet-opnsense` via os-git-backup) · Omada CT 525 (10.10.50.25) · PBS CT 240 (10.10.20.40; starts after Unraid NFS) · Unraid VM 2020 · HAOS VM 3050 (10.10.30.50) · Technitium 751 (10.10.70.51) / 750 (10.10.70.50) · athena CT 10030 (10.10.100.30) |
| Retire | ops VM 9090 (P1) · Management Caddy CT 635 (P1) · AdGuard 730/731 (P2) · docker-dmz VM 10015 + Arcane, Authentik CT 837 (P3) · template 9000 (P7) |
| Domain | `aliammar.net`: public DNS at Cloudflare (tunnel CNAMEs); split-horizon internal zone in Technitium |
| Gotchas | turn off ballooning on VMs · NixOS LXC serving :53 needs `services.resolved.enable = false` · recreating a guest on the same IP poisons OPNsense's ARP, so pin MACs · cloudflared needs public resolvers |

## Glue budget

| Glue | Size |
|---|---|
| `modules/{base,agent,docker-host}.nix` | ~250 lines |
| `modules/installer.nix` (no-touch installer ISO per host) | ~40 lines |
| `modules/nix-cache.nix` (ops serves its store on the LAN; harmonia) | ~60 lines |
| `.doco-cd.{admin,dmz}.yml` | ~10 lines each |
| comin → Discord post-deploy hook | ~10 lines |
| CI: flake check + `docker compose config` per stack + "routed app has gatus.yaml/README" check | ~60 lines |
| alert webhook → `claude -p` (P6) | ~40 lines |
| doco-cd MCP filter proxy (P6, optional) | ~40 lines |

Anything bigger needs a new row in Decisions.
