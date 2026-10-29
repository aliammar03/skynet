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
  `.claude/settings.json` allows the list/get tools (not `list_stacks`/`get_stack`: Swarm only) and
  `trigger_poll`. On `doco-admin` it denies `control_project`, `control_stack`, `destroy_project`,
  `remove_stack`, `trigger_scheduled_job` and `compact_mirrors` (operate lane, P6). On `doco-dmz`
  (D11) it allows `control_project`, `control_stack`, `trigger_scheduled_job` and `compact_mirrors`,
  and asks Ali before `destroy_project` and `remove_stack`. A session picks up `.mcp.json` and these
  rules when it starts.
- **PBS drift check:** `pbs-drift` (daily 07:00, `modules/pbs-drift.nix`) reads PBS's config over
  the agent's SSH key and compares it with `pbs/etc/` as deployed here. A difference, or a failed
  read, goes to `#alerts` (`discord_alerts_webhook`, passed as a systemd credential).
- **LAN Nix cache:** harmonia on :5000 (`modules/nix-cache.nix`) serves ops's store to every other host
  (they're clients via `base.nix`). ops admits 10.10.0.0/16, and the OPNsense alias
  `ROLE_NIX_CACHE_CLIENTS` decides which hosts get through: a new host needs adding there. `nix-cache-key` generates the signing key once
  in `/var/lib/nix-cache-key/`. Its public half is `hosts/ops/cache.pub`, which switches the clients
  on. A rebuilt ops gets a new key, so update `cache.pub`.
- **Permissions:** both sessions run in Claude Code **auto mode**: a classifier approves routine
  actions and sends anything risky to Ali as a Discord prompt. `.claude/settings.json` deny rules
  (merge, force-push, sudo on ops) and ask rules (doco-dmz's destroy and remove) apply in every mode.
- **Updates:** comin pulls `main` every 60 s.
- **Rebuild:** `proxmox.sh` on the node → boot the NixOS ISO → `nixos-anywhere --flake .#ops
  --target-host root@10.10.90.91 --generate-hardware-config nixos-generate-config
  hosts/ops/hardware.nix` → one-time `/login` and Discord pairing as `skynet`.
- **`installer.pub`:** the key nixos-anywhere uses to SSH into the NixOS installer (public; the
  installed system allows no root login).
- **State worth keeping:** `/home/skynet/.claude` (logins, plugin, memory), covered by PBS.
