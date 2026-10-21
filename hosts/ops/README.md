# ops

The agent's VM: Claude Code as user `skynet` (no sudo), reachable from Discord `#skynet` and the
Claude app. VMID 9091 · 10.10.90.91 · VLAN 90 · server-proxmox-core · 4 vCPU / 8 GB / 64 GB.

- **Sessions:** `skynet-agent` (tmux `skynet`: the persistent Discord + Remote Control conversation)
  and `skynet-spawn` (tmux `spawn`: on-demand sessions from the Claude app, one git worktree each).
  Each runs in its own tmux server. Watch or drive: `skynet-attach` (or `skynet-attach spawn`);
  detach with **F12**.
- **Secrets:** `secrets/ops.yaml` → `discord_bot_token`, `github_token` (aliammar-skynet PAT).
  `GH_TOKEN` reaches the sessions via their environment. The Discord token is written by
  `skynet-discord-token` to `~/.claude/channels/discord/.env`, the file the plugin reads, because
  Claude doesn't pass the session environment to plugin servers.
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
