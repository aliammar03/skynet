# New NixOS VM

From a free VMID to a host that comin keeps current, without anyone typing in a console.
docker-admin (P1) was built this way. **Agent** steps run on ops as `skynet`, from a checkout of
`main`; **Ali** steps are his.

## 0. Pick (agent, read-only)

- **IP and VMID:** VMID = VLAN + two-digit last octet (10.10.50.40 → 5040). The IP is unused
  (ping, OPNsense ARP `api/diagnostics/interface/get_arp`, Technitium), and the VMID is free on both
  nodes (Proxmox API `nodes/<node>/qemu` and `/lxc`). The nodes aren't clustered, so check each.
- **Room:** free RAM on the target node (`nodes/<node>/status`). VMs get `--balloon 0`.
- **MACs:** `BC:24:11:<vlan>:<octet>:<nic>`, e.g. `BC:24:11:50:40:01`. Pinned, so OPNsense's ARP
  entry stays valid across a rebuild.
- **VLAN tag:** every NIC is tagged, except VLAN 50 on server-proxmox-network (vmbr0's native VLAN
  there).

## 1. Installer PR (agent)

- `hosts/<h>/net.nix`: MACs, address, gateway, DNS (shared by the installer and the host).
- `hosts/<h>/proxmox.sh`: a copy of `hosts/docker-admin/proxmox.sh` with the VMID, name, cores,
  memory, disk, NICs (pinned MACs, tags) and `local:iso/nixos-installer-<h>.iso`.
- `hosts/<h>/README.md`: VMID · IP · node · size, then the bullets docker-admin's README has.
- `flake.nix`: `packages.${system}.installer-<h> = mkInstaller "<h>";`

## 2. Boot the installer

1. Agent: `nix build .#installer-<h>`, giving `result/iso/nixos-*.iso`: sshd on the host's IP, NIC
   matched by MAC, root reachable only with the agent's key (`hosts/ops/agent.pub`).
2. Ali, from the workstation. The copy goes ops → node over the LAN:
   `scp -3 aliammar@10.10.90.91:<iso path> root@<node>:/var/lib/vz/template/iso/nixos-installer-<h>.iso`
   (network node 10.10.50.10, core node 10.10.50.11).
3. Ali, on that node: run `hosts/<h>/proxmox.sh`. The VM boots the ISO.

## 3. Host PR (agent)

- `ssh root@<ip> nixos-generate-config --no-filesystems --show-hardware-config > hosts/<h>/hardware.nix`
- `hosts/<h>/default.nix`: hostName, NICs renamed by MAC (`systemd.network.links`), addresses from
  `net.nix`, imports `base.nix` plus its role module. `hosts/<h>/disk.nix`: docker-admin's (disko,
  `/dev/sda`, ESP + ext4).
- `flake.nix`: `nixosConfigurations.<h> = mkHost "<h>";`
- **Nothing that needs a secret yet.** The host has no age key until it's installed. Gate those parts
  on `hasSecret`, or add them in step 6. `base.nix` fails CI if the config uses a secret that
  `secrets/<h>.yaml` lacks.
- `nix flake check` passes → Ali merges.

## 4. Install (agent)

`nix run github:nix-community/nixos-anywhere -- --flake .#<h> --target-host root@<ip> --no-substitute-on-destination`

The whole closure goes from ops over the LAN. The VM reboots into NixOS: the boot order is disk
first, so the ISO can stay attached. From now on there's no root login; the agent's installer key
no longer works.

## 5. Identity PR (agent)

1. `ssh-keyscan -t ed25519 <ip> 2>/dev/null | cut -d' ' -f2- > hosts/<h>/ssh_host.pub`
2. `ssh-to-age < hosts/<h>/ssh_host.pub` → a key `&<h>` in `.sops.yaml` and a creation rule
   `^secrets/<h>\.yaml$` for `*aliammar` + `*<h>`. A Docker host also gets
   `^stacks/<target>/.*\.sops\.[^/]+$`.
3. `modules/agent.nix`: `programs.ssh.knownHosts.<h> = { hostNames = [ "<ip>" ]; publicKeyFile = ../hosts/<h>/ssh_host.pub; };`
   This pins the key for the agent's log access. `base.nix` already creates user `skynet` there:
   agent key from ops only, journal only.

## 6. Secrets (Ali, agent)

- Ali, for values he holds (e.g. `discord_alerts_webhook`, so comin posts failed deploys):
  `nix shell nixpkgs#sops -c sops secrets/<h>.yaml`
- Agent, for random values (passwords, API secrets). It writes the file straight from a generator,
  so the value is never shown:
  `printf 'my_secret: %s\n' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" | sops encrypt --filename-override secrets/<h>.yaml --input-type yaml --output-type yaml /dev/stdin > secrets/<h>.yaml`
  Only for a new file: the agent can't decrypt, so it can't add to an existing one. Ali adds keys
  with `sops` instead.
- Then the PR that enables what uses them. comin applies it within about a minute.

## 7. OPNsense (Ali)

- `ROLE_NIX_CACHE_CLIENTS` += the IP (ops's LAN Nix cache, :5000).
- A `HOST_<NAME>` alias, plus the role aliases and rules the host's job needs.
- Web egress is already allowed for every VLAN in `NET_WEB_EGRESS` (comin, caches, registries).

## 8. Check (agent)

- `ssh skynet@<ip> 'systemctl --failed; journalctl -u comin -n 20 -o cat'`: nothing failed, and
  comin is on main's HEAD.
- A Gatus row for what the host serves.
- `hosts/<h>/README.md` states the result.

## Rebuild

Steps 2 and 4 with the existing files. The rebuilt VM has a **new host key**, so redo step 5 and
have Ali run `nix shell nixpkgs#sops -c sops updatekeys secrets/<h>.yaml` (plus the host's stack
files) so they're encrypted for the new key.

## Gotchas

- VLAN 50 on the network node is untagged; everywhere else, tag.
- `--balloon 0`. A NixOS host serving :53 needs `services.resolved.enable = false`.
- Run `nix fmt` with file arguments (`nix fmt -- hosts/<h>/default.nix`); with none it waits on
  stdin.
