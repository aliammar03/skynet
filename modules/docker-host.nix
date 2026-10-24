# Docker hosts (docker-admin, docker-dmz): Docker, the networks stacks join (stacks never create
# networks; skynetv2.md → Conventions → Networks), and doco-cd, which deploys `stacks/<target>/` from
# `main`, with Apprise for its Discord notices.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  inherit (config.skynet.docker) macvlan doorNetworks docoTarget;
  creds = "/run/doco-cd"; # what doco-cd may read: its age key, API secret, Apprise URL
  # Same path inside and out, so stacks' relative bind mounts resolve. Holds doco-cd's checkout, with
  # the files this host can decrypt decrypted (root-only, like /run/secrets).
  data = "/var/lib/doco-cd";
in
{
  options.skynet.docker.macvlan = lib.mkOption {
    description = "The doors' macvlan: they get LAN IPs on this VLAN; an app only when a firewall rule names it.";
    type = lib.types.submodule {
      options = lib.genAttrs [ "name" "parent" "subnet" "gateway" ] (
        _: lib.mkOption { type = lib.types.str; }
      );
    };
  };

  options.skynet.docker.doorNetworks = lib.mkOption {
    type = lib.types.listOf lib.types.str;
    default = [ ];
    description = "Internal bridges, each shared by a door and one app with no login of its own, so no other container reaches that app.";
  };

  options.skynet.docker.docoTarget = lib.mkOption {
    type = lib.types.str;
    description = "doco-cd poll target: reads `.doco-cd.<target>.yml` from the repo.";
  };

  config = {
    virtualisation.docker = {
      enable = true;
      daemon.settings.log-driver = "journald";
    };
    # Weekly: images no container uses, pulled over a week ago. Not autoPrune (`docker system
    # prune`): it deletes stopped containers, and a doco-cd job's container (heartbeat) is stopped
    # between runs; doco-cd finds its jobs by those containers.
    systemd.services.docker-image-prune = {
      description = "Prune unused Docker images";
      requires = [ "docker.service" ];
      after = [ "docker.service" ];
      path = [ config.virtualisation.docker.package ];
      serviceConfig.Type = "oneshot";
      script = "docker image prune --all --force --filter until=168h";
      startAt = "weekly";
    };

    # `edge`: the bridge apps and doors share (doors reach apps by container name). `doorNetworks`:
    # a door and one app with no login, alone (internal: no route out). Create-only: a changed
    # macvlan subnet needs the network removed by hand. The macvlan has no `--ip-range`, so every
    # container on it sets a fixed `ipv4_address`; Docker would otherwise hand out VLAN IPs.
    systemd.services.docker-networks = {
      description = "Create the Docker networks stacks join";
      wantedBy = [
        "multi-user.target"
        "docker-doco-cd.service"
      ];
      requires = [ "docker.service" ];
      after = [ "docker.service" ];
      before = [ "docker-doco-cd.service" ];
      path = [ config.virtualisation.docker.package ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
      };
      script = ''
        docker network inspect edge >/dev/null 2>&1 || docker network create edge
        docker network inspect ${macvlan.name} >/dev/null 2>&1 || docker network create -d macvlan \
          --subnet ${macvlan.subnet} --gateway ${macvlan.gateway} -o parent=${macvlan.parent} ${macvlan.name}
      ''
      + lib.concatMapStrings (n: ''
        docker network inspect ${n} >/dev/null 2>&1 || docker network create --internal ${n}
      '') doorNetworks;
    };

    # doco-cd gets only these three files, never /run/secrets. Its age key is the host's own (from the
    # SSH host key), so it decrypts exactly what sops-nix can.
    systemd.services.doco-cd-credentials = {
      description = "Give doco-cd its age key, API secret and Apprise URL";
      wantedBy = [ "multi-user.target" ];
      before = [ "docker-doco-cd.service" ];
      requiredBy = [ "docker-doco-cd.service" ];
      path = [ pkgs.ssh-to-age ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        UMask = "0077";
      };
      script = ''
        install -d -m 700 ${creds}
        ssh-to-age -private-key -i /etc/ssh/ssh_host_ed25519_key > ${creds}/age.key
        install -m 400 ${config.sops.secrets.doco_api_secret.path} ${creds}/api-secret
        install -m 400 ${config.sops.secrets.discord_alerts_webhook.path} ${creds}/apprise-urls
      '';
    };
    # doco-cd reads the *_FILE values at start, so a changed secret restarts it too.
    sops.secrets =
      lib.genAttrs
        [
          "doco_api_secret"
          "discord_alerts_webhook"
        ]
        (_: {
          restartUnits = [
            "doco-cd-credentials.service"
            "docker-doco-cd.service"
          ];
        });
    systemd.tmpfiles.rules = [ "d ${data} 0700 root root -" ];

    virtualisation.oci-containers.backend = "docker";
    # Stateless Apprise API; doco-cd posts to it on loopback.
    virtualisation.oci-containers.containers.apprise = {
      image = "docker.io/caronc/apprise:2.0.1@sha256:0b2913b15c8eb47c25345722985ffbfae701326edde21909c205d296d62dd52c";
      ports = [ "127.0.0.1:8000:8000" ];
      # One gevent worker serves a few notices a day; the default is 2 × CPUs + 1 (13 on docker-dmz,
      # ~740 MB).
      environment.APPRISE_WORKER_COUNT = "1";
      # The image declares these volumes; stateless notices keep nothing there, so no anonymous ones.
      extraOptions = [
        "--tmpfs=/attach"
        "--tmpfs=/config"
        "--tmpfs=/plugin"
      ];
    };
    # Host networking, so the NixOS firewall governs its ports (a published port would bypass it).
    virtualisation.oci-containers.containers.doco-cd = {
      image = "ghcr.io/kimdre/doco-cd:0.129.1@sha256:9c6e7f0040056465cdbc762b608c8893c64e691d464e34928c14338a6eaf6b8f";
      dependsOn = [ "apprise" ];
      extraOptions = [
        "--network=host"
        "--cap-drop=ALL"
      ];
      volumes = [
        "/var/run/docker.sock:/var/run/docker.sock"
        "${data}:${data}"
        "${creds}:${creds}:ro"
      ];
      environment = {
        TZ = config.time.timeZone;
        # Every poll is five info lines a minute. Deploys still reach #alerts and the MCP
        # (list_deployment_runs); failures are errors.
        LOG_LEVEL = "warn";
        HTTP_PORT = "8080"; # API, /mcp, /v1/health; metrics stay on 9120
        DATA_MOUNT_PATH = data;
        DATA_HOST_PATH = data;
        SOPS_AGE_KEY_FILE = "${creds}/age.key";
        API_SECRET_FILE = "${creds}/api-secret";
        MCP_ENABLED = "true";
        APPRISE_API_URL = "http://127.0.0.1:8000/notify";
        APPRISE_NOTIFY_URLS_FILE = "${creds}/apprise-urls";
        APPRISE_NOTIFY_LEVEL = "success";
        POLL_CONFIG = builtins.toJSON [
          {
            url = "https://github.com/aliammar03/skynet.git";
            reference = "main";
            interval = "60s";
            target = docoTarget;
          }
        ];
      };
    };
    # The doco-cd API and MCP answer only to ops (OPNsense must allow it too).
    networking.firewall.extraCommands = ''
      iptables -A nixos-fw -p tcp -s 10.10.90.91 --dport 8080 -j nixos-fw-accept
    '';
  };
}
