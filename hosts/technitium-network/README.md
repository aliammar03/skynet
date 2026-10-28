# technitium-network

DNS server: Technitium, configured only from `dns/` (skynetv2.md → P2, `dns/README.md`).
VMID 7050 · 10.10.70.50 · server-proxmox-network · 2 vCPU / 1 GB / 16 GB.

- **NIC** (MAC pinned in `proxmox.sh`, matched in `net.nix`): `lan` = net0, tag 70.
- **Install / rebuild:** `runbooks/new-vm.md`: the installer ISO
  (`nix build .#installer-technitium-network`) boots first, then nixos-anywhere installs with
  `--copy-host-keys` so the host keeps the key its sops recipient was made from.
- **DNS** (`modules/dns.nix`):
  - Technitium answers on :53 and serves its UI and API on :5380 (http://10.10.70.50:5380);
  - `technitium-sync` applies `dns/settings.json` and `dns/aliammar.net.zone` at boot and on every
    deploy that changes them, so UI edits last only until the next sync;
  - logs go to the journal (`journalctl -u technitium-dns-server -u technitium-sync`);
  - the host resolves through its own Technitium, then technitium-core (`net.nix`);
  - `gratuitous-arp` announces the address once it's up, so OPNsense learns a new MAC at once;
  - zram swap absorbs comin's evaluation on 1 GB;
  - `technitium-stats.timer` writes the dashboard's last hour every 5 minutes for node-exporter
    (`/var/lib/node-exporter/technitium.prom`): queries by response and by how they were answered,
    clients, cache (`DnsFailing`, `DnsStatsStale`).
- **Secrets** (`secrets/technitium-network.yaml`): `technitium_admin_password` (agent-generated; it
  sets `admin`'s password on the first start only), `discord_alerts_webhook`.
- **Agent access:** user `skynet`, the agent's key from 10.10.90.91 only, group `systemd-journal`;
  no sudo. Its host key is `ssh_host.pub`, pinned in ops's known_hosts for both IPs.
