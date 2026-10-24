# docker-dmz

Apps Docker host: doco-cd (target `dmz`), the apps, their doors caddy-apps (10.10.100.35) and
cloudflared (.33), and the apps' own Authelia (portal `login`) (skynetv2.md → P3).
VMID 10010 · 10.10.100.10 · server-proxmox-core · 6 vCPU / 10 GB / 128 GB.

- **NIC** (MAC pinned in `proxmox.sh`, matched in `net.nix`): `dmz` = net0, tag 100. It carries the
  host IP and is the parent of the `dmz` macvlan. The host and the macvlan's containers can't reach
  each other directly, and nothing needs them to.
- **Install / rebuild:** `runbooks/new-vm.md`: the installer ISO (`nix build .#installer-docker-dmz`)
  boots first, then nixos-anywhere installs with `--copy-host-keys` so the host keeps the key its
  sops recipient was made from. The ISO comes up on 10.10.100.10 with only the agent's key for root;
  the installed system doesn't trust that key.
- **Docker:** `modules/docker-host.nix`, with journald logs and a weekly image prune. The
  `docker-networks` unit creates `edge` (bridge) and `dmz` (macvlan on NIC `dmz`, 10.10.100.0/24);
  stacks only join them, and every container on `dmz` sets a fixed `ipv4_address`.
- **doco-cd** (`modules/docker-host.nix`): polls `main` every 60 s, target `dmz` → `.doco-cd.dmz.yml`
  → every folder in `stacks/dmz/`. API, `/mcp` and `/v1/health` on :8080 are for ops only (MCP
  `doco-dmz`). Deploy notices go to `#alerts` via Apprise (loopback :8000).
- **Secrets** (`secrets/docker-dmz.yaml`): `doco_api_secret`, `discord_alerts_webhook`.
- **Agent access:** user `skynet`, the agent's key from 10.10.90.91 only, groups `systemd-journal`
  and `wheel`: **root via passwordless sudo** (D11), Docker included (`sudo docker …`). Every sudo
  command lands in the journal (`journalctl _COMM=sudo`). Its host key is `ssh_host.pub`, pinned in
  ops's known_hosts. MCP `doco-dmz` may also restart stacks and run jobs (`hosts/ops/README.md`).

## v1's data (P3, once)

Done 2026-10-24: all 21 paths arrived with v1's sizes and owners, and 10015 is off. Ali copied v1's
app data from VM 10015 (10.10.100.15, Docker off) after the install and before the apps deploy
(skynetv2.md → P3 → Data). One `rsync` per path, as root on both ends, so owners and
modes stay (`--numeric-ids`: CouchDB runs as 5984, Mongo as 999). The volume names are v1's
`<project>_<volume>`; a wrong path stops only its line, with "No such file or directory".

From a workstation shell whose agent holds the key (`eval "$(ssh-agent -s)"; ssh-add`; `ssh-add -l`
lists it), `ssh -A aliammar@10.10.100.15`, where `ssh-add -l` lists it too. Then:

1. One at a time, because they can prompt:
   ```sh
   sudo -v
   command -v rsync >/dev/null && command -v curl >/dev/null || sudo apt-get install -y rsync curl
   sudo install -d -m 700 /root/.ssh
   curl -fsSL https://raw.githubusercontent.com/aliammar03/skynet/main/hosts/docker-dmz/ssh_host.pub | sed 's/^/10.10.100.10 /' | sudo tee -a /root/.ssh/known_hosts
   ```
   The last line prints `10.10.100.10 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPYe7/5kzdaippYiP01MB+bleeBIQITJESEMrAU1/HWb`
   (fingerprint `SHA256:KAmUg2H0OdSThbxu8LErVg762NQwe9voi5KQocXfmYg`): root's ssh now trusts
   docker-dmz's key from the repo, so the copy never stops to ask.
2. The copy, pasted as one block. `--preserve-env=SSH_AUTH_SOCK` lets root's ssh use your forwarded
   key.
   ```sh
   copy() { sudo --preserve-env=SSH_AUTH_SOCK rsync -aHAX --numeric-ids --mkpath --rsync-path='sudo rsync' "$1/" "aliammar@10.10.100.10:/opt/appdata/$2/"; }
   A=/opt/docker/appdata V=/var/lib/docker/volumes
   copy $A/librespeed/data                        librespeed/data         # 20K
   copy $V/obsidian-livesync_data/_data           obsidian/couchdb        # 13M
   copy $A/karakeep/data                          karakeep/data           # 1.8G
   copy $V/karakeep_meili_data/_data              karakeep/meili          # 6.5M
   copy $A/paperless-ngx/data                     paperless/data          # 15M, the four together
   copy $A/paperless-ngx/media                    paperless/media
   copy $A/paperless-ngx/consume                  paperless/consume
   copy $A/paperless-ngx/export                   paperless/export
   copy $A/calibre/config                         calibre/config          # 2.4G
   copy $A/silly/config                           sillytavern/config      # 17M, the four together
   copy $A/silly/data                             sillytavern/data
   copy $A/silly/plugins                          sillytavern/plugins
   copy $A/silly/extensions                       sillytavern/extensions
   copy $A/marinara/data                          marinara/data           # 841M
   copy $V/aiometadata_jikan_mongo_data/_data     jikan/mongo             # 995M
   copy $V/aiometadata_jikan_typesense_data/_data jikan/typesense         # 71M
   copy $V/aiometadata_jikan_redis_data/_data     jikan/redis             # 4.4M
   copy $A/aiometadata/data                       aiometadata/data        # 25M
   copy $A/aiometadata/cold-store                 aiometadata/cold-store  # 46M
   copy $V/aiometadata_redis_data/_data           aiometadata/redis       # 176M
   copy $A/aiostreams/data                        aiostreams/data         # 142M
   ```
   aiometadata's `poster-cache` (8.9G) stays behind: it refills.
3. Compare the sizes, then power 10015 off:
   ```sh
   sudo --preserve-env=SSH_AUTH_SOCK ssh aliammar@10.10.100.10 "sudo du -sh /opt/appdata/*/*"
   sudo poweroff
   ```
