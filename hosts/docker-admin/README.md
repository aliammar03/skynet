# docker-admin

Admin Docker host: doco-cd (target `admin`), caddy-admin, Authelia, Gatus (skynetv2.md → P1).
VMID 5040 · 10.10.50.40 · server-proxmox-network · 2 vCPU / 4 GB / 32 GB.

- **NICs** (MACs pinned in `proxmox.sh`, matched in `net.nix`): `lan` = net0, untagged, because VLAN
  50 is vmbr0's native VLAN on this node; `adm60` = net1, tag 60, no host IP (caddy-admin's macvlan
  parent).
- **Install:** `nix build .#installer-docker-admin` on ops → copy the ISO to the node's `local:iso`
  as `nixos-installer-docker-admin.iso` → `proxmox.sh` → `nixos-anywhere --flake .#docker-admin --target-host root@10.10.50.40 --no-substitute-on-destination` from ops (closure copied over the LAN). The ISO comes up
  on 10.10.50.40 with only the agent's key for root; the installed system doesn't trust that key.
- **Docker:** `modules/docker-host.nix`, with journald logs and a weekly prune. The `docker-networks`
  unit creates `edge` (bridge) and `adm60` (macvlan on NIC `adm60`, 10.10.60.0/24); stacks only join them.
- **doco-cd** (`modules/docker-host.nix`): polls `main` every 60 s, target `admin` →
  `.doco-cd.admin.yml` → every folder in `stacks/admin/`. API, `/mcp` and `/v1/health` on :8080 are
  for ops only. Deploy notices go to `#alerts` via Apprise (loopback :8000).
- **Secrets** (`secrets/docker-admin.yaml`): `doco_api_secret`, `discord_alerts_webhook`.
- **Agent access:** user `skynet`, the agent's key from 10.10.90.91 only, group `systemd-journal`
  (reads all logs, e.g. `journalctl CONTAINER_NAME=doco-cd`); no sudo, no Docker socket. Its host key
  is `ssh_host.pub`, pinned in ops's known_hosts.
