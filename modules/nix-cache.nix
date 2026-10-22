# ops serves its Nix store to the other hosts over the LAN (harmonia, :5000), so they fetch what ops
# already has from it instead of from cache.nixos.org. The signing key belongs to ops, like an SSH
# host key: generated once on first boot, never in git. Its public half, hosts/ops/cache.pub, is what
# switches the clients on; until it exists in git the clients don't use the cache.
{ config, lib, ... }:
let
  url = "http://10.10.90.91:5000";
  pub = ../hosts/ops/cache.pub;
  # ops admits the whole lab; OPNsense alias ROLE_NIX_CACHE_CLIENTS decides which hosts get through.
  # Every host but ops is a client via base.nix, so a new host only needs adding to that alias.
  keyDir = "/var/lib/nix-cache-key";
  isOps = config.networking.hostName == "ops";
in
lib.mkMerge [
  (lib.mkIf isOps {
    systemd.services.nix-cache-key = {
      description = "Generate the LAN cache's signing key";
      wantedBy = [ "multi-user.target" ];
      before = [ "harmonia.service" ];
      path = [ config.nix.package ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        UMask = "0077";
      };
      script = ''
        mkdir -p ${keyDir}
        if [ ! -e ${keyDir}/sign.sec ]; then
          nix key generate-secret --key-name ops-cache-1 > ${keyDir}/sign.sec
          nix key convert-secret-to-public < ${keyDir}/sign.sec > ${keyDir}/sign.pub
          chmod 644 ${keyDir}/sign.pub
        fi
      '';
    };
    systemd.services.harmonia = {
      requires = [ "nix-cache-key.service" ];
      after = [ "nix-cache-key.service" ];
    };
    services.harmonia.cache = {
      enable = true;
      signKeyPaths = [ "${keyDir}/sign.sec" ];
      settings.priority = 30; # ahead of cache.nixos.org (40)
    };
    networking.firewall.extraCommands = ''
      iptables -A nixos-fw -p tcp -s 10.10.0.0/16 --dport 5000 -j nixos-fw-accept
    '';
  })

  (lib.mkIf (!isOps && builtins.pathExists pub) {
    nix.settings = {
      extra-substituters = [ url ];
      extra-trusted-public-keys = [ (lib.fileContents pub) ];
      connect-timeout = 5; # ops down → fall back to cache.nixos.org quickly
    };
  })
]
