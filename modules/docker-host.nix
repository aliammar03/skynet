# Docker hosts (docker-admin, docker-dmz): Docker, plus the networks stacks join. Stacks never create
# networks (skynetv2.md → Conventions → Networks).
{ config, lib, ... }:
let
  inherit (config.skynet.docker) macvlan;
in
{
  options.skynet.docker.macvlan = lib.mkOption {
    description = "The doors' macvlan: they get LAN IPs on this VLAN; apps never do.";
    type = lib.types.submodule {
      options = lib.genAttrs [ "name" "parent" "subnet" "gateway" ] (
        _: lib.mkOption { type = lib.types.str; }
      );
    };
  };

  config = {
    virtualisation.docker = {
      enable = true;
      daemon.settings.log-driver = "journald";
      autoPrune = {
        enable = true;
        dates = "weekly";
      };
    };

    # `edge`: the bridge apps and doors share (doors reach apps by container name).
    systemd.services.docker-networks = {
      description = "Create the Docker networks stacks join";
      wantedBy = [ "multi-user.target" ];
      requires = [ "docker.service" ];
      after = [ "docker.service" ];
      path = [ config.virtualisation.docker.package ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
      };
      script = ''
        docker network inspect edge >/dev/null 2>&1 || docker network create edge
        docker network inspect ${macvlan.name} >/dev/null 2>&1 || docker network create -d macvlan \
          --subnet ${macvlan.subnet} --gateway ${macvlan.gateway} -o parent=${macvlan.parent} ${macvlan.name}
      '';
    };
  };
}
