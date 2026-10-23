# technitium-network addressing, shared by its installer ISO and its host config. The MAC is pinned in
# proxmox.sh, so the right NIC gets the IP and OPNsense's ARP entry survives a rebuild.
{
  lan = {
    mac = "bc:24:11:70:50:01";
    address = "10.10.70.50/24";
    gateway = "10.10.70.1";
  };
  # The other DNS server: the installer resolves through it, the host after its own Technitium.
  dns = [ "10.10.70.51" ];
}
