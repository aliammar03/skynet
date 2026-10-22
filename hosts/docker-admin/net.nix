# docker-admin addressing, shared by its installer ISO and its host config. The MACs are pinned in
# proxmox.sh, so the right NIC gets the IP and OPNsense's ARP entry survives a rebuild.
{
  # VLAN 50 is vmbr0's untagged VLAN on server-proxmox-network: net0 carries no tag.
  lan = {
    mac = "bc:24:11:50:40:01";
    address = "10.10.50.40/24";
    gateway = "10.10.50.1";
  };
  # VLAN 60, no host IP: the macvlan parent for caddy-admin (10.10.60.60).
  adm60.mac = "bc:24:11:50:40:60";
  dns = [
    "10.10.70.51"
    "10.10.70.50"
  ];
}
