# ops

The agent's VM: Claude Code as user `skynet` (no sudo), reachable from Discord `#skynet` and the
Claude app. VMID 9091 · 10.10.90.91 · VLAN 90 · server-proxmox-core · 4 vCPU / 6 GB (8 until its
next restart) / 64 GB.

- **Sessions:** `skynet-agent` (tmux `skynet`: the persistent Discord + Remote Control conversation)
  and `skynet-spawn` (tmux `spawn`: on-demand sessions from the Claude app, one git worktree each).
  Each runs in its own tmux server. Watch or drive: `skynet-attach` (or `skynet-attach spawn`);
  detach with **F12**.
- **Interactive sessions:** `skynet-claude <name>` (a-z, 0-9, -) attaches to the agent's session
  `<name>`, or starts it: one tmux session (server `claude`, as `skynet`) and one git worktree
  (`.claude/worktrees/<name>`) per name, with Remote Control on under that name. A name whose worktree
  holds a conversation (after `/exit` or a reboot) continues it; a new name starts with a blank
  prompt. `skynet-claude` alone lists the running ones. Run it from a plain shell, not inside tmux.
- **tmux, mouse:** drag to highlight, right-click to copy to the workstation's clipboard, Ctrl+click
  a link (Ctrl+Shift+click if tmux takes it). tmux passes the clipboard (OSC 52) and links (OSC 8) to
  the terminal, so this works over SSH in Windows Terminal; sessions set `FORCE_HYPERLINK=1` so Claude
  Code prints real links.
- **Secrets:** `secrets/ops.yaml` → `discord_bot_token`, `github_token` (aliammar-skynet PAT).
  `GH_TOKEN` reaches the sessions via their environment. The Discord token is written by
  `skynet-discord-token` to `~/.claude/channels/discord/.env`, the file the plugin reads, because
  Claude doesn't pass the session environment to plugin servers.
- **Read-only lab APIs:** `pve_core_read_token`, `pve_network_read_token` (`skynet@pve!read`,
  PVEAuditor on `/`, one per standalone node) and `opnsense_read_key` / `opnsense_read_secret`
  (user `skynet-read`, config writes denied). sops-nix renders them into files under
  `/run/secrets/rendered/` (owner `skynet`, 0400) that curl reads itself:
  - `curl -sS --cacert stacks/admin/caddy-admin/certs/proxmox-core.pem -H @/run/secrets/rendered/pve-core.header https://10.10.50.11:8006/api2/json/…`
    (`pve-network.header` and `proxmox-network.pem` → `10.10.50.10`): the nodes' own CAs, pinned in
    caddy-admin for the browser path; their certs name the IPs;
  - `curl -sk --netrc-file /run/secrets/rendered/opnsense.netrc https://10.10.50.1/api/…`: `-k`,
    because its pinned cert names a host, not the IP.
- **P8's apps (D16):** `komga_password` (`secrets/ops.komga.yaml`) and `uchiyomi_password`
  (`secrets/ops.uchiyomi.yaml`), the agent's admin accounts, through caddy-apps like any visitor:
  - `curl --netrc-file /run/secrets/rendered/komga.netrc https://komga.aliammar.net/api/…` (HTTP
    Basic as `skynet@aliammar.net`); the claim, once:
    `curl -X POST -H @/run/secrets/rendered/komga-claim.header https://komga.aliammar.net/api/v1/claim`;
  - `uchiyomi-login.json` is the body of `POST /api/setup` (once) and `POST /auth/login` (user
    `skynet`), which answers a 15-minute JWT (`accessToken`): keep it in a 0600 file, never in a
    transcript.
- **doco-cd MCP (`doco-admin`, `doco-dmz` in `.mcp.json`):** `doco_<target>_api_key` (= that Docker
  host's `doco_api_secret`) is rendered to `/run/secrets/rendered/doco-<target>.headers.json`, which
  Claude Code's `headersHelper` prints as the `x-api-key` header. For each server,
  `.claude/settings.json` allows the list/get tools (not `list_stacks`/`get_stack`: Swarm only),
  `trigger_poll`, and the operate lane's `control_project`, `control_stack`, `trigger_scheduled_job`
  and `compact_mirrors` (D11), and asks Ali before `destroy_project` and `remove_stack`. A session
  picks up `.mcp.json` and these rules when it starts.
- **PBS drift check:** `pbs-drift` (daily 07:00, `modules/pbs-drift.nix`) reads PBS's config over
  the agent's SSH key and compares it with `pbs/etc/` as deployed here. A difference, or a failed
  read, goes to `#alerts` (`discord_alerts_webhook`, passed as a systemd credential).
- **Unattended runs** (`modules/agent-runs.nix`, P6):
  - `skynet-incident`, each minute, hands each new alert group in Alertmanager to a headless run, at
    most 8 a day. `skynet-digest` (08:00) and `skynet-report` (Mondays 08:30) post the morning
    digest and the weekly report.
  - Each is a `skynet-run`: `claude -p --restricted` with AGENTS.md, its runbook
    (`runbooks/incident.md`, `digest.md`, `report.md`) and its data. It only reads: the repo,
    VictoriaMetrics, VictoriaLogs, and doco-cd's list and get tools.
  - `skynet-post` posts the answer to `#skynet` as the bot. Its token is `discord-bot.header`, a
    sops template curl reads.
  - State is in `/var/lib/skynet-runs`, with the reports kept 14 days.
  - By hand, as skynet: `DRY_RUN=1 skynet-digest` prints instead of posting, and
    `touch /var/lib/skynet-runs/paused` stops the incident runs.
- **LAN Nix cache:** harmonia on :5000 (`modules/nix-cache.nix`) serves ops's store to every other host
  (they're clients via `base.nix`). ops admits 10.10.0.0/16, and the OPNsense alias
  `ROLE_NIX_CACHE_CLIENTS` decides which hosts get through: a new host needs adding there. `nix-cache-key` generates the signing key once
  in `/var/lib/nix-cache-key/`. Its public half is `hosts/ops/cache.pub`, which switches the clients
  on. A rebuilt ops gets a new key, so update `cache.pub`.
- **Tailscale:** on Ali's tailnet as `tag:ops` (D14), userspace, so ops's own routes and DNS are
  unchanged. `ssh <machine>.<tailnet>.ts.net` goes through `tailscale nc` (`programs.ssh`, `Host
  *.ts.net`); what `tag:ops` may reach is set in the tailnet policy (Ali's admin console).
  `tailscale_authkey` (`secrets/ops.yaml`, tagged `tag:ops`) serves the first login only; the node
  key then stays in `/var/lib/tailscale`. A rebuilt ops needs a fresh key.
- **Permissions:** both sessions run in Claude Code **auto mode**: a classifier approves routine
  actions and sends anything risky to Ali as a Discord prompt. `.claude/settings.json` deny rules
  (merge, force-push, sudo on ops) and ask rules (doco-dmz's destroy and remove) apply in every mode.
- **Updates:** comin pulls `main` every 60 s.
- **Rebuild** (not drilled; restoring the guest from PBS is the quicker way back,
  `runbooks/restore.md`, case 4). ops is the one host the agent can't install, since it runs there:
  1. **Ali**, on the core node: the NixOS ISO,
     `wget -P /var/lib/vz/template/iso https://channels.nixos.org/nixos-26.05/latest-nixos-minimal-x86_64-linux.iso`,
     then `proxmox.sh`.
  2. **Ali**, in the VM's console: `sudo -i`, `ip -br link`, then
     `ip addr add 10.10.90.91/24 dev <if>; ip route add default via 10.10.90.1; echo nameserver 10.10.70.51 > /etc/resolv.conf`,
     and the installing machine's public key into `~/.ssh/authorized_keys`.
  3. From that machine, on VLAN 90 or the workstation:
     `nix run github:nix-community/nixos-anywhere -- --flake .#ops --target-host root@10.10.90.91 --generate-hardware-config nixos-generate-config hosts/ops/hardware.nix`.
     The new `hardware.nix`, the new recipient (`ssh-keyscan -t ed25519 10.10.90.91 | ssh-to-age`
     in `.sops.yaml`) and the new `agent.pub` and `cache.pub` go in a PR; Ali re-encrypts
     `secrets/ops*.yaml` for the new key and puts the new agent key on PBS (`runbooks/restore.md`,
     case 3).
  4. **Ali**, in the agent's session (`ssh aliammar@10.10.90.91`, then `skynet-attach`):
     `/login` (the Claude subscription), trust `~/skynet`, accept Remote Control,
     `/plugin install discord@claude-plugins-official`; DM the bot, then `/discord:access pair <code>`
     and `/discord:access policy allowlist`; then `claude remote-control` once, interactively, to
     accept its prompt.
- **`installer.pub`:** the key the first install's nixos-anywhere used: v1's ops key
  (`svc-ops@vm-skynet-ops`, VM 9090's, destroyed 2026-10-25). Nothing reads it now; step 2 uses the
  installing machine's own key.
- **The Discord bot** "Skynet" (Ali's Developer Portal app): Message Content Intent on, invited to
  the server with View Channels, Send Messages, Send in Threads, Read Message History, Attach Files
  and Add Reactions.
- **State worth keeping:** `/home/skynet/.claude` (logins, plugin, memory), covered by PBS.
