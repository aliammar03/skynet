# docker-admin

Admin Docker host: doco-cd (target `admin`), caddy-admin, Authelia, Gatus (skynetv2.md → P1).
VMID 5040 · 10.10.50.40 · server-proxmox-network · 2 vCPU / 4 GB / 32 GB.

- **NICs** (MACs pinned in `proxmox.sh`, matched in `net.nix`): `lan` = net0, untagged, because VLAN
  50 is vmbr0's native VLAN on this node; `adm60` = net1, tag 60, no host IP (caddy-admin's macvlan
  parent).
- **Install:** `nix build .#installer-docker-admin` on ops → copy the ISO to the node's `local:iso`
  as `nixos-installer-docker-admin.iso` → `proxmox.sh` → `nixos-anywhere` from ops. The ISO comes up
  on 10.10.50.40 with only the agent's key for root; the installed system doesn't trust that key.
