# New NixOS VM: one PR

Any role: a Docker host, a DNS server, anything NixOS. **One PR per VM** (or one for a pair). The
installer boots from the branch first, so the PR can carry the VM's real hardware and host key, its
sops recipient and its secrets. After the merge, nixos-anywhere installs it with that same host key,
and everything starts on the first boot. comin keeps it current from then on.

**Agent** steps run on ops as `skynet`; **Ali** steps are his. `<h>` is the host's name; an
existing host (e.g. `hosts/docker-admin/`) is the template for each file.

## 0. Pick (agent, read-only)

- **IP and VMID:** VMID = VLAN + two-digit last octet (10.10.50.40 → 5040). The IP is unused
  (ping, OPNsense ARP `api/diagnostics/interface/get_arp`, Technitium), and the VMID is free on both
  nodes (Proxmox API `nodes/<node>/qemu` and `/lxc`). The nodes aren't clustered, so check each.
- **Room:** free RAM on the target node (`nodes/<node>/status`). Ballooning: Gotchas.
- **MACs:** `BC:24:11:XX:YY:NN`, where XX:YY are the VMID's last four digits (5040 → `50:40`,
  7050 → `70:50`, 10010 → `00:10`) and NN numbers the NIC (`01`, `02`…). Pinned, so OPNsense's ARP
  entry stays valid across a rebuild. docker-admin's second NIC (`:60`) predates this rule.
- **VLAN tag:** every NIC is tagged, except VLAN 50 on server-proxmox-network (vmbr0's native VLAN
  there).

## 1. Branch (agent)

On `p<N>/<h>`:
- `hosts/<h>/net.nix`: MACs, address, gateway, DNS. Both the installer and the host read it.
- `hosts/<h>/proxmox.sh`: copy an existing host's, then change the VMID, name, cores, memory, disk
  size and NICs (pinned MACs, tags). Keep the rest:
  - OVMF with an efidisk;
  - `scsi0` on `local-lvm`;
  - `--serial0 socket`, `--agent enabled=1`, `--onboot 1`;
  - `--boot order=scsi0;ide2`, disk first, which step 5 relies on;
  - `local:iso/nixos-installer-<h>.iso` on `ide2`.
- `hosts/<h>/default.nix`: hostName, NICs renamed by MAC (`systemd.network.links`), addresses from
  `net.nix`, `base.nix` plus the role's module. `hosts/<h>/disk.nix`: disko, `/dev/sda`, ESP + ext4
  (docker-dmz's: ESP, a 64 GiB ext4 root and 128 GiB of btrfs for `/opt/appdata`, with
  `skynet.docker.appdataSnapshots`).
- `hosts/<h>/README.md`: VMID · IP · node · size, its NICs, install line, secrets, agent access.
- `flake.nix`: `nixosConfigurations.<h> = mkHost "<h>";` and
  `packages.${system}.installer-<h> = mkInstaller "<h>";`
- A Docker host also needs the files under **Docker host** below.
- Push the branch, then `nix build .#installer-<h>`: sshd on the host's IP, NIC matched by MAC, root
  reachable only with the agent's key (`hosts/ops/agent.pub`). Copy from `readlink -f result/iso/*.iso`,
  the store path: the `result` link sits in skynet's home, which Ali can't read.

## 2. Boot the installer (Ali)

1. Copy the ISO ops → node over the LAN, from the workstation:
   `scp -3 aliammar@10.10.90.91:<store path of the iso> root@<node>:/var/lib/vz/template/iso/nixos-installer-<h>.iso`
   (network node 10.10.50.10, core node 10.10.50.11).
2. On the node, run the branch's `proxmox.sh`:
   `curl -fsSL https://raw.githubusercontent.com/aliammar03/skynet/refs/heads/<branch>/hosts/<h>/proxmox.sh -o /root/proxmox-<h>.sh`,
   read it, then `sh /root/proxmox-<h>.sh`. The VM boots the ISO.
3. OPNsense:
   - a `HOST_<NAME>` alias with the IP. Nest it, not the IP, in `ROLE_NIX_CACHE_CLIENTS` (ops's
     LAN Nix cache, :5000), `ROLE_METRICS_TARGETS` and `ROLE_LOG_SHIPPERS` (docker-admin scrapes
     it and takes its journal, rules 236 and 237), and in the role aliases the host's job needs, then
     add its rules. A later IP change then edits only the `HOST_` alias;
   - check that its VLAN is in `NET_WEB_EGRESS` (20, 50, 60, 70, 80, 90, 100). comin, the caches and
     the registries need :443. If it isn't, add an egress rule.

   DNS (rule 100) and NTP (rule 130) already cover every Skynet VLAN. ops reaches every Skynet VLAN
   on any port (rule 390), so SSH and doco-cd's :8080 need nothing.

**Don't reboot the installer before step 5.** It makes a new host key on every boot, and step 3
records the current one. If it reboots anyway, redo steps 3.1–3.3 and 3.5, and Ali re-adds his
values.

## 3. Read the VM, finish the PR (agent)

1. Scan the key, then use it for the connection. The key is new, so ssh can't ask about it, and a
   rebuild's old pin would refuse it:
   ```sh
   kh=$(mktemp); ssh-keyscan -t ed25519 <ip> 2>/dev/null > "$kh"
   cut -d' ' -f2- "$kh" > hosts/<h>/ssh_host.pub
   ssh -o UserKnownHostsFile="$kh" -o GlobalKnownHostsFile=/dev/null root@<ip> \
     nixos-generate-config --no-filesystems --show-hardware-config > hosts/<h>/hardware.nix
   ```
   Step 5 keeps this key, so it becomes the installed host's key.
2. `.sops.yaml`: a key `&<h>` = `ssh-to-age < hosts/<h>/ssh_host.pub`, and a creation rule
   `^secrets/<h>\.yaml$` for `*aliammar` + `*<h>`.
3. `modules/agent.nix`: `programs.ssh.knownHosts.<h> = { hostNames = [ "<ip>" ]; publicKeyFile = ../hosts/<h>/ssh_host.pub; };`
   List every IP the host will have (e.g. a build IP and a final IP). This pins the key for the
   agent's log access; `base.nix` already creates user `skynet` there (agent key from ops only,
   journal only).
4. The Gatus row for what the host serves (`stacks/admin/gatus/config/admin.yaml`). It alerts until
   step 5 finishes, so expect one DOWN and one RESOLVED. Its metrics and logs: its `node` and
   `comin` targets in `stacks/admin/metrics/scrape.yaml` (and `cadvisor`, `doco-cd` for a Docker
   host), and its IP in docker-admin's list of log shippers (`hosts/docker-admin/default.nix`).
   `base.nix` already runs its exporters and ships its journal.
5. **All** random secrets in one command, before Ali adds his. The agent can't decrypt, so it can
   only create the file whole, never add to it:
   `printf 'one: %s\ntwo: %s\n' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" | sops encrypt --filename-override secrets/<h>.yaml --input-type yaml --output-type yaml /dev/stdin > secrets/<h>.yaml`
   The values are never shown. With no random secrets, Ali creates the file in step 4.
6. `nix fmt -- <changed .nix files>`, `nix flake check`, push, open the PR. It says which values
   Ali must add.

## 4. Secrets and merge (Ali)

On the branch, `nix shell nixpkgs#sops -c sops secrets/<h>.yaml` to add the values only he holds:
`discord_alerts_webhook` (the `#alerts` URL; every host needs it, so comin can post failed deploys)
and whatever the role needs. Commit and push.

CI fails while `secrets/<h>.yaml` lacks any secret the config uses, the webhook included
(`base.nix`), so green means the host's secrets are complete. Stack secrets aren't checked by CI: a
missing one fails that stack's deploy, which posts to `#alerts`. Merge.

## 5. Install (agent, from `main`)

Once ops has applied the merge, its known_hosts pins the key
(`ssh-keygen -F <ip> -f /etc/ssh/ssh_known_hosts` finds it). Then:

`nix run --inputs-from . nixpkgs#nixos-anywhere -- --flake .#<h> --target-host root@<ip> --copy-host-keys --no-substitute-on-destination`

- Our ISO identifies as a NixOS installer (`VARIANT_ID=installer`), so nixos-anywhere installs from
  it directly. `--copy-host-keys` keeps its host key: the one in `ssh_host.pub`, so sops decrypts on
  the first boot.
- While this runs, the agent is root on the installer, which holds that private key. It reads only
  the public half (D11).
- The closure goes from ops over the LAN, with the flake's pinned nixos-anywhere. The VM reboots
  into NixOS from its disk (the ISO can stay attached). From now on there's no root login.
- A Docker host also gets the doco-cd hold, so no app starts before its data is there: add
  `--extra-files "$h"` to the line, after
  `h=$(mktemp -d); mkdir -p "$h/var/lib/skynet"; touch "$h/var/lib/skynet/hold-doco-cd"`.

## 6. Check (agent)

`ssh skynet@<ip> 'systemctl --failed; journalctl -u comin -n 20 -o cat'`: nothing failed, comin is
on main's HEAD, and the Gatus row is green.

A Docker host waits with doco-cd held. `skynet-restore … --all` releases it once the data is back
(Rebuild, step 4). Otherwise (a new host with no data, or data copied back from ops), as root, the
agent where it has sudo, else Ali: with `skynet.docker.appdataSnapshots`,
`systemctl start btrbk-appdata` first, so the backup job finds a snapshot; then
`rm /var/lib/skynet/hold-doco-cd && systemctl start docker-doco-cd`.

## Docker host (also in the PR)

- `default.nix`: import `../../modules/docker-host.nix` and set:
  - `skynet.docker.docoTarget = "<target>";`
  - `skynet.docker.macvlan` (name, parent NIC, subnet, gateway), which is required (no default),
    plus that NIC in `net.nix` and `proxmox.sh`. It's the doors' VLAN.
- `.doco-cd.<target>.yml`: a copy of `.doco-cd.admin.yml` with `working_dir: stacks/<target>`.
  `stacks/<target>/` gets its first stack.
- `.sops.yaml`: also `^stacks/<target>/.*\.sops\.[^/]+$` for `*aliammar` + `*<h>`.
- `secrets/<h>.yaml`: `doco_api_secret` among the random values (step 3.5), next to Ali's
  `discord_alerts_webhook`.
- A dead-man: copy `compose.yaml`, `.doco-cd.yml` and `README.md` from `stacks/admin/heartbeat/`
  into `stacks/<target>/heartbeat/`. Not its `secret.sops.env`: that's encrypted for docker-admin.
  Drop the `gatus:8080` condition, because Gatus runs only on docker-admin. Ali adds a healthchecks.io
  check and creates the secret file with its `HC_PING_URL`.
- The agent's read-only MCP, on ops:
  - `secrets/ops.yaml` gets `doco_<target>_api_key`, the same value. Ali copies it (it fails rather
    than writing an empty value):
    `nix shell nixpkgs#sops nixpkgs#jq -c bash -c 'set -o pipefail; sops -d --extract "[\"doco_api_secret\"]" secrets/<h>.yaml | jq -R . | sops set --value-stdin secrets/ops.yaml "[\"doco_<target>_api_key\"]"'`
  - `modules/agent.nix`: its header template, as for `doco-admin`;
  - `.mcp.json`: server `doco-<target>` (`http://<ip>:8080/mcp`, `headersHelper`);
  - `.claude/settings.json`: `doco-<target>` in `enabledMcpjsonServers`, and `doco-admin`'s
    allow/deny lists with the `mcp__doco-<target>__` prefix.
- `runbooks/new-stack.md`: the host's column in "Values per Docker host".

## Rebuild

1. A Docker host that still runs copies its data to ops first, cold (skynetv2.md → P4 → The
   rebuild). On the host, comin and doco-cd first, so nothing restarts what stops next (a comin
   switch would start doco-cd again):
   `sudo systemctl stop comin docker-doco-cd && sudo docker ps -q | xargs -r sudo docker stop`.
   Then on ops, `/opt/appdata` into one tar, and the tar compared with it file by file:
   ```sh
   mkdir -p -m 700 ~/rebuild
   ssh skynet@<ip> 'sudo tar -C /opt/appdata --exclude=./backup --numeric-owner -cf - .' > ~/rebuild/<h>-appdata.tar
   ssh skynet@<ip> 'sudo tar -C /opt/appdata --numeric-owner -df -' < ~/rebuild/<h>-appdata.tar
   ```
   Both exit 0. The first warns only of sockets, which the apps make again; the second prints
   nothing. `./backup` is restic's old cache, now on `/var/cache`. The stacks stay stopped. On a
   host where the agent has no sudo (docker-admin), Ali runs these from the workstation with his
   own user.
2. Ali takes a PBS backup of the VM (Backup now, storage `pbs`), the fallback. Then he stops and
   destroys it: `qm stop <vmid> && qm destroy <vmid>`. Destroying is his call, and `qm create`
   refuses an existing VMID. disko wipes the disk, so `/opt/appdata` comes back only from step 1's
   copy or from Drive.
3. Steps 1–6 with the existing files. The fresh ISO boot has a new key, so the PR updates
   `ssh_host.pub`, the `.sops.yaml` recipient and the agent's pin (the old pin would refuse the new
   key). Ali re-encrypts every file of the host's for it, then pushes. sops takes a file's format
   from its extension and doesn't know `.conf`, so the rclone configs (INI) need `--input-type`:
   `nix shell nixpkgs#sops -c sh -c 'for f in secrets/<h>.yaml stacks/<target>/*/*.sops.*; do case "$f" in *.conf) sops updatekeys -y --input-type ini "$f" ;; *) sops updatekeys -y "$f" ;; esac || echo "FAILED: $f"; done'`.
   `git status --short` then lists every one of them, and the agent checks each file's recipients
   before the merge. Install with `--copy-host-keys` again, and on a Docker host the doco-cd hold.
4. A Docker host's data, as root, while doco-cd is still held:
   - from step 1's copy, then compared again, as in step 1:
     ```sh
     ssh skynet@<ip> 'sudo tar -C /opt/appdata --numeric-owner -xf -' < ~/rebuild/<h>-appdata.tar
     ssh skynet@<ip> 'sudo tar -C /opt/appdata --numeric-owner -df -' < ~/rebuild/<h>-appdata.tar
     ```
     then doco-cd's release, as for a new host (step 6). The copy stays on ops until Ali says it
     can go;
   - from Drive, if the host was lost: `skynet-restore drive --all [<snapshot>]` (default
     `latest`). It puts every stack back, takes the first local snapshot (with
     `appdataSnapshots`), then releases doco-cd, which deploys the stacks onto their data.

## Gotchas

- VLAN 50 on the network node is untagged; everywhere else, tag.
- **Ballooning:** `--memory` is the most a VM gets, `--balloon` the least. Proxmox keeps the minimum
  guaranteed and reclaims the rest, mostly page cache, only once the node passes 80% use.
  - Give a minimum of the working set plus headroom (`free -m`'s used, not its cache) to a guest
    that is well under its memory: the Docker hosts and ops.
  - `--balloon 0` (off) for PCI passthrough (OPNsense, Unraid), whose memory is pinned whole
    anyway, and for small critical guests (the 1 GB DNS VMs).
  - A changed setting applies at the VM's next start (`qm reboot <vmid>`).
- A NixOS host serving :53 needs `services.resolved.enable = false`.
- A Docker host's first deploy pulls every image at once (docker-dmz: 22 GB in about 5 minutes). A
  registry timeout fails that run and posts to `#alerts`, and doco-cd's next pass deploys the rest.
- Run `nix fmt` with file arguments; with none it waits on stdin.
