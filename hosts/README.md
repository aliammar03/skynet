# hosts

One folder per NixOS host, each built by `flake.nix` (`mkHost`) and kept current by comin
(ADR-0002). A new one follows `runbooks/new-vm.md`, in one PR.

| File | Content |
|---|---|
| `default.nix` | the host: its name, NICs renamed by MAC, addresses from `net.nix`, `modules/base.nix` plus its role's module |
| `net.nix` | MACs, address, gateway, DNS; the installer reads it too |
| `disk.nix` | disko's layout |
| `hardware.nix` | read from the running installer |
| `proxmox.sh` | the exact `qm create` (ADR-0010) |
| `ssh_host.pub` | the host key, pinned in ops's known_hosts (`modules/agent.nix`) |
| `README.md` | VMID · address · node · size, its NICs, install line, secrets, agent access |

ops, the first host and the agent's home, keeps its address in `default.nix` and has no
`ssh_host.pub`: the agent works from it, not into it. Its folder also holds the agent's public key
(`agent.pub`), the LAN cache's (`cache.pub`) and the installer's (`installer.pub`).

A host's own secrets are `secrets/<host>.yaml` (sops-nix). The machines git configures that
aren't NixOS have folders of their own: PBS `pbs/`, the Proxmox nodes `pve/`, Unraid `unraid/`.

## Addressing

- VMID = VLAN + the last octet in two digits: 10.10.50.40 is 5040, 10.10.100.10 is 10010.
- Static addresses through networkd. NICs are renamed by MAC: `lan`, `adm60`, `dmz`.
- MACs are pinned: `BC:24:11:XX:YY:NN`, XX:YY the VMID's last four digits, NN the NIC
  (`runbooks/new-vm.md`, step 0). Recreating a guest on the same address with a new MAC poisons
  OPNsense's ARP entry.
- VLAN 50 is vmbr0's native VLAN on both nodes, so a NIC on it carries no tag; every other NIC is
  tagged.

## Keys

- A host's age identity comes from its SSH host key (`ssh-to-age`). sops-nix decrypts with it, and
  on the Docker hosts doco-cd does too; `.sops.yaml` names it as the recipient of the host's files.
- The installer makes the key; nixos-anywhere's `--copy-host-keys` keeps it, so the installed host
  decrypts its secrets on its first boot.
- A restore from PBS keeps the key. A reinstall from scratch makes a new one: the PR updates
  `ssh_host.pub`, the recipient and the agent's pin, and Ali re-encrypts every file of the host's
  (`runbooks/new-vm.md` → Rebuild).
- `modules/base.nix` asserts that every secret a host uses is in its file, so CI fails rather than
  the switch on the host.

## Gotchas

- **Ballooning,** per VM (`runbooks/new-vm.md` → Gotchas): a minimum for the Docker hosts and ops,
  off for the passthrough guests (OPNsense, Unraid) and the DNS VMs.
- A NixOS host that serves :53 needs `services.resolved.enable = false`: resolved's stub holds :53.
