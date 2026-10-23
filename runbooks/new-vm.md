# New NixOS VM: one PR

**One PR per VM** (or one for a pair, like P2's DNS servers). The installer boots from the branch
first, so the PR can carry the VM's real hardware and host key, its sops recipient and its secrets.
After the merge, nixos-anywhere installs it with that same host key, and everything starts on the
first boot. comin keeps it current from then on.

**Agent** steps run on ops as `skynet`; **Ali** steps are his.

## 0. Pick (agent, read-only)

- **IP and VMID:** VMID = VLAN + two-digit last octet (10.10.50.40 → 5040). The IP is unused
  (ping, OPNsense ARP `api/diagnostics/interface/get_arp`, Technitium), and the VMID is free on both
  nodes (Proxmox API `nodes/<node>/qemu` and `/lxc`). The nodes aren't clustered, so check each.
- **Room:** free RAM on the target node (`nodes/<node>/status`). VMs get `--balloon 0`.
- **MACs:** `BC:24:11:<vlan>:<octet>:<nic>`, e.g. `BC:24:11:50:40:01`. Pinned, so OPNsense's ARP
  entry stays valid across a rebuild.
- **VLAN tag:** every NIC is tagged, except VLAN 50 on server-proxmox-network (vmbr0's native VLAN
  there).

## 1. Branch (agent)

On `p<N>/<host>`:
- `hosts/<h>/net.nix`: MACs, address, gateway, DNS. Both the installer and the host read it.
- `hosts/<h>/proxmox.sh`: a copy of `hosts/docker-admin/proxmox.sh` with the VMID, name, cores,
  memory, disk, NICs (pinned MACs, tags) and `local:iso/nixos-installer-<h>.iso`.
- `hosts/<h>/default.nix`: hostName, NICs renamed by MAC (`systemd.network.links`), addresses from
  `net.nix`, `base.nix` plus the role module. `hosts/<h>/disk.nix`: docker-admin's (disko,
  `/dev/sda`, ESP + ext4).
- `hosts/<h>/README.md`: VMID · IP · node · size, then the bullets docker-admin's README has.
- `flake.nix`: `nixosConfigurations.<h> = mkHost "<h>";` and
  `packages.${system}.installer-<h> = mkInstaller "<h>";`
- Push the branch, then `nix build .#installer-<h>`, giving `result/iso/nixos-*.iso`: sshd on the
  host's IP, NIC matched by MAC, root reachable only with the agent's key (`hosts/ops/agent.pub`).

## 2. Boot the installer (Ali)

1. Copy the ISO ops → node over the LAN, from the workstation:
   `scp -3 aliammar@10.10.90.91:<iso path> root@<node>:/var/lib/vz/template/iso/nixos-installer-<h>.iso`
   (network node 10.10.50.10, core node 10.10.50.11).
2. On the node, run the branch's `proxmox.sh`:
   `curl -fsSL https://raw.githubusercontent.com/aliammar03/skynet/refs/heads/<branch>/hosts/<h>/proxmox.sh -o /root/proxmox-<h>.sh`,
   read it, then `sh /root/proxmox-<h>.sh`. The VM boots the ISO.
3. OPNsense: `ROLE_NIX_CACHE_CLIENTS` += the IP (ops's LAN Nix cache, :5000), a `HOST_<NAME>` alias,
   and the role aliases and rules the host's job needs. Web egress (comin, caches, registries)
   already covers every VLAN in `NET_WEB_EGRESS`.

**Don't reboot the installer before step 5.** It makes a new host key on every boot, and step 3
records the current one.

## 3. Read the VM, finish the PR (agent)

1. `ssh root@<ip> nixos-generate-config --no-filesystems --show-hardware-config > hosts/<h>/hardware.nix`
2. `ssh-keyscan -t ed25519 <ip> 2>/dev/null | cut -d' ' -f2- > hosts/<h>/ssh_host.pub`.
   Step 5 keeps this key, so it becomes the installed host's key.
3. `.sops.yaml`: a key `&<h>` = `ssh-to-age < hosts/<h>/ssh_host.pub`, and a creation rule
   `^secrets/<h>\.yaml$` for `*aliammar` + `*<h>`. A Docker host also gets
   `^stacks/<target>/.*\.sops\.[^/]+$`.
4. `modules/agent.nix`: `programs.ssh.knownHosts.<h> = { hostNames = [ "<ip>" ]; publicKeyFile = ../hosts/<h>/ssh_host.pub; };`
   This pins the key for the agent's log access. `base.nix` already creates user `skynet` there:
   agent key from ops only, journal only.
5. Random secrets (passwords, API secrets) go straight from a generator into the new file, so the
   values are never shown:
   `printf 'my_secret: %s\n' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" | sops encrypt --filename-override secrets/<h>.yaml --input-type yaml --output-type yaml /dev/stdin > secrets/<h>.yaml`
6. `nix fmt -- <changed .nix files>`, `nix flake check`, push, open the PR. It says which values
   Ali must add.

## 4. Secrets and merge (Ali)

On the branch: `nix shell nixpkgs#sops -c sops secrets/<h>.yaml` to add the values only he holds
(e.g. `discord_alerts_webhook`, so comin posts failed deploys). Commit and push. CI fails while any
secret the config uses is missing (`base.nix`), so green means complete. Merge.

## 5. Install (agent, from `main`)

`nix run github:nix-community/nixos-anywhere -- --flake .#<h> --target-host root@<ip> --copy-host-keys --no-substitute-on-destination`

- Our ISO identifies as a NixOS installer (`VARIANT_ID=installer`), so nixos-anywhere installs from
  it directly. `--copy-host-keys` keeps its host key: the one in `ssh_host.pub`, so sops decrypts on
  the first boot.
- The closure goes from ops over the LAN. The VM reboots into NixOS; the boot order is disk first,
  so the ISO can stay attached. From now on there's no root login.

## 6. Check (agent)

- `ssh skynet@<ip> 'systemctl --failed; journalctl -u comin -n 20 -o cat'`: nothing failed, and
  comin is on main's HEAD.
- A Gatus row for what the host serves. It goes in the PR if the host's address is known up front.

## Rebuild

The same steps with the existing files: boot the ISO, then rescan the key in step 3. A fresh ISO
boot makes a new key, so the PR updates `ssh_host.pub` and the `.sops.yaml` recipient, and Ali runs
`nix shell nixpkgs#sops -c sops updatekeys <file>` for each file the host decrypts. Install with
`--copy-host-keys` again.

## Gotchas

- VLAN 50 on the network node is untagged; everywhere else, tag.
- `--balloon 0`. A NixOS host serving :53 needs `services.resolved.enable = false`.
- Run `nix fmt` with file arguments; with none it waits on stdin.
