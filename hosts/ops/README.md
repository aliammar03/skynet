# ops

The agent's VM: Claude Code as user `skynet` (no sudo), reachable from Discord `#skynet` and the
Claude app. VMID 9091 · 10.10.90.91 · VLAN 90 · server-proxmox-core · 4 vCPU / 8 GB / 64 GB.

- **Sessions:** `skynet-agent` (tmux `skynet`: the persistent Discord + Remote Control conversation)
  and `skynet-spawn` (tmux `spawn`: on-demand sessions from the Claude app, one git worktree each).
  Each runs in its own tmux server. Watch or drive: `skynet-attach` (or `skynet-attach spawn`);
  detach with **F12**. `skynet-claude` starts a fresh terminal session as the agent in its own
  worktree.
- **Secrets:** `secrets/ops.yaml` → `discord_bot_token`, `github_token` (aliammar-skynet PAT).
  `GH_TOKEN` reaches the sessions via their environment. The Discord token is written by
  `skynet-discord-token` to `~/.claude/channels/discord/.env`, the file the plugin reads, because
  Claude doesn't pass the session environment to plugin servers.
- **Read-only lab APIs:** `pve_core_read_token`, `pve_network_read_token` (`skynet@pve!read`,
  PVEAuditor on `/`, one per standalone node) and `opnsense_read_key` / `opnsense_read_secret`
  (user `skynet-read`, config writes denied). sops-nix renders them into files under
  `/run/secrets/rendered/` (owner `skynet`, 0400) that curl reads itself:
  - `curl -sk -H @/run/secrets/rendered/pve-core.header https://10.10.50.11:8006/api2/json/…`
    (`pve-network.header` → `10.10.50.10`);
  - `curl -sk --netrc-file /run/secrets/rendered/opnsense.netrc https://10.10.50.1/api/…`.

  `-k` because both use self-signed certs (caddy-admin pins them for the browser path).
- **doco-cd MCP (`doco-admin` in `.mcp.json`):** `doco_admin_api_key` (= docker-admin's
  `doco_api_secret`) is rendered to `/run/secrets/rendered/doco-admin.headers.json`, which Claude
  Code's `headersHelper` prints as the `x-api-key` header. `.claude/settings.json` allows the
  list/get tools (not `list_stacks`/`get_stack`: Swarm only) and `trigger_poll`, and denies `control_project`, `control_stack`,
  `destroy_project`, `remove_stack`, `trigger_scheduled_job` and `compact_mirrors` (operate lane,
  P6). A session picks up `.mcp.json` when it starts.
- **LAN Nix cache:** harmonia on :5000 (`modules/nix-cache.nix`) serves ops's store to every other host
  (they're clients via `base.nix`). ops admits 10.10.0.0/16, and the OPNsense alias
  `ROLE_NIX_CACHE_CLIENTS` decides which hosts get through: a new host needs adding there. `nix-cache-key` generates the signing key once
  in `/var/lib/nix-cache-key/`. Its public half is `hosts/ops/cache.pub`, which switches the clients
  on. A rebuilt ops gets a new key, so update `cache.pub`.
- **Permissions:** both sessions run in Claude Code **auto mode**: a classifier approves routine
  actions and sends anything risky to Ali as a Discord prompt. `.claude/settings.json` deny rules
  (merge, force-push, sudo) apply in every mode.
- **Updates:** comin pulls `main` every 60 s.
- **Rebuild:** `proxmox.sh` on the node → boot the NixOS ISO → `nixos-anywhere --flake .#ops
  --target-host root@10.10.90.91 --generate-hardware-config nixos-generate-config
  hosts/ops/hardware.nix` → one-time `/login` and Discord pairing as `skynet`.
- **`installer.pub`:** the key nixos-anywhere uses to SSH into the NixOS installer (public; the
  installed system allows no root login).
- **State worth keeping:** `/home/skynet/.claude` (logins, plugin, memory), covered by PBS.
