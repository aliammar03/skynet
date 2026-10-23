# technitium-core addressing, shared by its installer ISO and its host config. The MAC is pinned in
# proxmox.sh, so the right NIC gets the IP and OPNsense's ARP entry survives a rebuild.
{
  # Build IP, beside the old CT 751 on .51; its cutover PR moves it to 10.10.70.51.
  lan = {
    mac = "bc:24:11:70:51:01";
    address = "10.10.70.53/24";
    gateway = "10.10.70.1";
  };
  # The other DNS server: the installer resolves through it, the host after its own Technitium.
  dns = [ "10.10.70.50" ];
}
