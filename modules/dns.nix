# DNS servers (technitium-network, technitium-core): Technitium, configured only from dns/ in git.
# technitium-sync applies dns/settings.json and dns/aliammar.net.zone through Technitium's HTTP API
# at boot and on every deploy that changes them (skynetv2.md → P2, dns/README.md).
{
  config,
  lib,
  pkgs,
  ...
}:
let
  address = lib.head config.systemd.network.networks."10-lan".address; # e.g. 10.10.70.52/24
  ip = lib.head (lib.splitString "/" address);
  # sops-nix's file is root-only; systemd hands each unit its own copy (both run as dynamic users).
  credential = "admin-password:${config.sops.secrets.technitium_admin_password.path}";
  sync = pkgs.writeShellApplication {
    name = "technitium-sync";
    runtimeInputs = [
      pkgs.curl
      pkgs.jq
    ];
    text = builtins.readFile ./technitium-sync.sh;
  };
  stats = pkgs.writeShellApplication {
    name = "technitium-stats";
    runtimeInputs = [
      pkgs.curl
      pkgs.jq
    ];
    text = builtins.readFile ./technitium-stats.sh;
  };
in
{
  services.resolved.enable = false; # its stub would hold :53
  # openresolv writes resolv.conf, and with a local server listed it drops the rest by default. Keep
  # the other server too, so comin can still reach GitHub if Technitium here is down.
  networking.resolvconf.extraConfig = "resolv_conf_local_only=NO";

  services.technitium-dns-server = {
    enable = true;
    openFirewall = true; # who may reach it is OPNsense's call
    firewallTCPPorts = [
      53
      5380 # web UI and API, plain HTTP (caddy-admin serves it with a cert)
    ];
  };
  sops.secrets.technitium_admin_password = { };
  systemd.services.technitium-dns-server = {
    environment = {
      DNS_SERVER_DOMAIN = config.networking.hostName;
      # admin's password, read on the very first start only. Technitium falls back to admin/admin
      # if it can't read this file; systemd refuses to start the unit when the credential is missing.
      DNS_SERVER_ADMIN_PASSWORD_FILE = "%d/admin-password";
    };
    serviceConfig = {
      LoadCredential = credential;
      OOMScoreAdjust = -500; # on a full 1 GB, the kernel kills a deploy's evaluation, not DNS
    };
  };
  zramSwap.enable = true; # comin evaluates the flake here; zram absorbs that peak

  systemd.services.technitium-sync = {
    description = "Apply dns/ (settings, aliammar.net) to Technitium";
    wantedBy = [ "multi-user.target" ];
    requires = [ "technitium-dns-server.service" ];
    after = [ "technitium-dns-server.service" ];
    # The files' store paths are part of the unit, so a deploy that changes dns/ re-runs it.
    environment = {
      SETTINGS = "${../dns/settings.json}";
      ZONE_FILE = "${../dns/aliammar.net.zone}";
      PASSWORD_FILE = "%d/admin-password";
    };
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      DynamicUser = true;
      LoadCredential = credential;
      ExecStart = lib.getExe sync;
    };
  };

  # The dashboard's last hour, every 5 minutes, for node-exporter's textfile collector (skynetv2.md →
  # P5 → Wider eyes): DnsFailing, and the answers' mix for the agent. It logs in as the sync does; a
  # failed run is UnitFailed, and a stale file DnsStatsStale. node-exporter's folder is root's, so a
  # root step (+) moves the file in whole: a scrape never reads half of it.
  systemd.services.technitium-stats = {
    description = "Write Technitium's last hour for node-exporter";
    requires = [ "technitium-dns-server.service" ];
    after = [ "technitium-dns-server.service" ];
    environment.PASSWORD_FILE = "%d/admin-password";
    serviceConfig = {
      Type = "oneshot";
      DynamicUser = true;
      LoadCredential = credential;
      RuntimeDirectory = "technitium-stats";
      ExecStart = lib.getExe stats;
      ExecStartPost = [
        "+${pkgs.coreutils}/bin/install -m 644 %t/technitium-stats/technitium.prom /var/lib/node-exporter/technitium.prom.tmp"
        "+${pkgs.coreutils}/bin/mv /var/lib/node-exporter/technitium.prom.tmp /var/lib/node-exporter/technitium.prom"
      ];
    };
  };
  systemd.timers.technitium-stats = {
    wantedBy = [ "timers.target" ];
    timerConfig.OnCalendar = "*:0/5";
  };

  # When a VM takes over .50/.51 from an old CT, OPNsense learns the new MAC at once instead of when
  # its ARP entry expires. The address is in the unit, so a cutover deploy re-runs it.
  systemd.services.gratuitous-arp = {
    description = "Announce ${ip} on lan";
    wantedBy = [ "multi-user.target" ];
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    path = [
      pkgs.iproute2
      pkgs.iputils
    ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      for _ in $(seq 30); do
        ip -4 -o addr show dev lan | grep -qF ' ${address} ' && break
        sleep 1
      done
      arping -U -c 3 -I lan ${ip}
    '';
  };
}
