# docker-dmz addressing, shared by its installer ISO and its host config. The MAC is pinned in
# proxmox.sh, so the right NIC gets the IP and OPNsense's ARP entry survives a rebuild.
{
  # VLAN 100, tagged: the host IP, and the parent of the `dmz` macvlan (the doors and the apps a
  # firewall rule names).
  dmz = {
    mac = "bc:24:11:00:10:01";
    address = "10.10.100.10/24";
    gateway = "10.10.100.1";
  };
  dns = [
    "10.10.70.51"
    "10.10.70.50"
  ];
}
