# docker-dmz

Apps Docker host: doco-cd (target `dmz`), the apps, their doors caddy-apps (10.10.100.35) and
cloudflared (.33), and the apps' own Authelia (portal `login`) (skynetv2.md → P3).
VMID 10010 · 10.10.100.10 · server-proxmox-core · 6 vCPU / 12 GB (10 guaranteed) / 193 GB.

- **NIC** (MAC pinned in `proxmox.sh`, matched in `net.nix`): `dmz` = net0, tag 100. It carries the
  host IP and is the parent of the `dmz` macvlan. The host and the macvlan's containers can't reach
  each other directly, and nothing needs them to.
- **Install / rebuild:** `runbooks/new-vm.md`: the installer ISO (`nix build .#installer-docker-dmz`)
  boots first, then nixos-anywhere installs with `--copy-host-keys` so the host keeps the key its
  sops recipient was made from. The ISO comes up on 10.10.100.10 with only the agent's key for root;
  the installed system doesn't trust that key.
- **Disk** (`disk.nix`, 193 GiB thin on `local-lvm`): ESP, a 64 GiB ext4 root (NixOS, the Nix
  store, Docker's images), and 128 GiB of btrfs for the apps' data: its top level at
  `/mnt/appdata-pool`, subvolume `@appdata` at `/opt/appdata`, subvolume `@snapshots`.
- **Data:** `/opt/appdata` began as v1's (2026-10-24, skynetv2.md → P3 → Data). It comes back from
  a snapshot or Drive now (`runbooks/restore.md`).
- **Snapshots** (btrbk, `skynet.docker.appdataSnapshots`): `@appdata`, read-only, at 04:20, as
  `@snapshots/@appdata.<YYYYMMDDThhmm>`, with `latest` pointing at the newest. Every one is kept for
  2 days, then one a day for 7. The backup job copies `latest` at 04:30; `skynet-restore local`
  restores from any (`stacks/dmz/backup/README.md`).
- **Docker:** `modules/docker-host.nix`, with journald logs and a weekly image prune. The
  `docker-networks` unit creates `edge` (bridge), `dmz` (macvlan on NIC `dmz`, 10.10.100.0/24) and
  the door networks `door-calibre`, `door-kapowarr`, `door-komga`, `door-mylar3`, `door-sabnzbd`,
  `door-suwayomi`, `door-uchiyomi` (internal, each shared by caddy-apps and one app); stacks only
  join them, and every container on `dmz` sets a fixed `ipv4_address`.
- **Storage** (P8): Unraid's share `Storage` (`10.10.20.20:/mnt/user/Storage`) at `/mnt/storage`, NFS
  4.2, mounted on first access and kept (the containers' bind mounts hold it), `hard`. Unraid's
  export admits this host read-write and writes everything as `nobody:users` (99:100, all_squash);
  OPNsense rule 300 carries it. Comics and manga live in `Books/Manga/` and `Books/Comics/`, each
  with Ali's own files in `library/` and the downloaders' beside them (`uchiyomi/`, `suwayomi/`, and
  `Comics/kapowarr/` and `Comics/mylar3/`). The share isn't in this host's backups.
- **doco-cd** (`modules/docker-host.nix`): polls `main` every 60 s, target `dmz` → `.doco-cd.dmz.yml`
  → every folder in `stacks/dmz/`. API, `/mcp` and `/v1/health` on :8080 are for ops only (MCP
  `doco-dmz`). Deploy notices go to `#alerts` via Apprise (loopback :8000).
- **Observability** (P5): node-exporter :9100, cAdvisor :9338, comin :4243 and doco-cd's :9120,
  for docker-admin only (`modules/observability.nix`). The journal goes to docker-admin's vlagent
  (:9429): the DMZ's one opening into the management VLAN, write-only.
- **Secrets** (`secrets/docker-dmz.yaml`): `doco_api_secret`, `discord_alerts_webhook`.
- **Agent access:** user `skynet`, the agent's key from 10.10.90.91 only, groups `systemd-journal`
  and `wheel`: **root via passwordless sudo** (D11), Docker included (`sudo docker …`). Every sudo
  command lands in the journal (`journalctl _COMM=sudo`). Its host key is `ssh_host.pub`, pinned in
  ops's known_hosts. MCP `doco-dmz` may also restart stacks and run jobs (`hosts/ops/README.md`).
