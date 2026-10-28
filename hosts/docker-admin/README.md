# docker-admin

Admin Docker host: doco-cd (target `admin`), caddy-admin, Authelia, Gatus (skynetv2.md → P1).
VMID 5040 · 10.10.50.40 · server-proxmox-network · 2 vCPU / 4 GB / 32 GB.

- **NICs** (MACs pinned in `proxmox.sh`, matched in `net.nix`): `lan` = net0, untagged, because VLAN
  50 is vmbr0's native VLAN on this node; `adm60` = net1, tag 60, no host IP (caddy-admin's macvlan
  parent).
- **Install / rebuild:** `runbooks/new-vm.md`: the installer ISO
  (`nix build .#installer-docker-admin`) boots first, then nixos-anywhere installs with
  `--copy-host-keys` so the host keeps the key its sops recipient was made from. The ISO comes up on
  10.10.50.40 with only the agent's key for root; the installed system doesn't trust that key.
- **Docker:** `modules/docker-host.nix`, with journald logs and a weekly prune. The `docker-networks`
  unit creates `edge` (bridge) and `adm60` (macvlan on NIC `adm60`, 10.10.60.0/24); stacks only join them.
- **doco-cd** (`modules/docker-host.nix`): polls `main` every 60 s, target `admin` →
  `.doco-cd.admin.yml` → every folder in `stacks/admin/`. API, `/mcp` and `/v1/health` on :8080 are
  for ops only. Deploy notices go to `#alerts` via Apprise (loopback :8000).
- **PBS's datastore:** `/mnt/pbs-datastore`, Unraid's share `pbs` over NFS 4.2, read-only and
  mounted on first access (`default.nix`), for `stacks/admin/pbs-offsite/`. Unraid's export maps
  this host to uid 34 (PBS's `backup`, the datastore's owner); OPNsense lets it reach Unraid on
  TCP 2049.
- **Observability** (P5): the `metrics`, `logs`, `alertmanager`, `grafana` and `exporters` stacks.
  Firewall rules in `default.nix`: its own containers reach this host's exporters and vlagent from a
  Docker bridge; vlagent (:9429, on the host's network) admits the hosts that ship their journal,
  the Proxmox nodes included; and each appliance that logs by syslog reaches only its own vlagent
  port (OPNsense, from 10.10.50.1, TCP 5514);
  tmpfiles rules give Alertmanager (`nobody`) and Grafana (472) their folders. Like every host, it runs node-exporter and the
  journal upload (`modules/observability.nix`), and cAdvisor on :9338 (`modules/docker-host.nix`).
- **Secrets** (`secrets/docker-admin.yaml`): `doco_api_secret`, `discord_alerts_webhook`.
- **Agent access:** user `skynet`, the agent's key from 10.10.90.91 only, group `systemd-journal`
  (reads all logs, e.g. `journalctl CONTAINER_NAME=doco-cd`); no sudo, no Docker socket. Its host key
  is `ssh_host.pub`, pinned in ops's known_hosts.
