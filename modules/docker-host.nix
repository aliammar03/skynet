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

    # `skynet-restore`: app data back from the nightly backup (stacks/<target>/backup/README.md). In
    # place, the stack's `backup-restore` job does it, so doco-cd holds the stateful services
    # stopped meanwhile. --list and --to run that job's container definition directly (its image,
    # secrets and mounts), with nothing stopped.
    environment.systemPackages = [
      (pkgs.writeShellApplication {
        name = "skynet-restore";
        runtimeInputs = [
          config.virtualisation.docker.package
          pkgs.coreutils
          pkgs.curl
          pkgs.systemd
        ];
        text = ''
          usage() {
            echo "usage: skynet-restore <stack> [snapshot] [--to <dir>]   (snapshot: default latest)"
            echo "       skynet-restore --all [snapshot]                  every stack, for a rebuilt host"
            echo "       skynet-restore --list [stack]                    the snapshots"
            exit 2
          }
          [ "$(id -u)" = 0 ] || { echo "skynet-restore: run it as root" >&2; exit 1; }
          job=backup-restore # doco-cd keeps the job's container, created, between runs
          inspect() { docker container inspect -f "$1" "$job"; }
          image=$(inspect '{{.Config.Image}}') || { echo "skynet-restore: no $job; is stack backup deployed?" >&2; exit 1; }
          direct() { # <extra docker run args…> -- <run.sh args…>
            local opts=()
            while [ "$1" != -- ]; do opts+=("$1"); shift; done
            shift
            docker run --rm --env-file <(inspect '{{range .Config.Env}}{{println .}}{{end}}') \
              --volumes-from "$job" --tmpfs /resticprofile --hostname "$(inspect '{{.Config.Hostname}}')" \
              "''${opts[@]}" --entrypoint /bin/sh "$image" /etc/resticprofile/run.sh "$@"
          }
          in_place() { # <stack|all> <snapshot>: the request, then the job, which consumes it
            mkdir -p /opt/appdata/backup
            printf '%s %s\n' "$1" "$2" >/opt/appdata/backup/restore.request
            local start out
            start=$(date +%s)
            out=$(curl -sS -X POST -w '\n%{http_code}' -H @<(printf 'x-api-key: %s\n' "$(cat /run/doco-cd/api-secret)") \
              "http://127.0.0.1:8080/v1/api/job/$job/run?stack=backup&wait=true")
            journalctl --since "@$start" -o cat IMAGE_NAME="$image" | tail -n 30
            echo "doco-cd: ''${out%$'\n'*}"
            [ "''${out##*$'\n'}" = 200 ]
          }
          name() { [[ $1 =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "skynet-restore: '$1' isn't a stack name" >&2; exit 2; }; }
          case "''${1:-}" in
          --list)
            direct -- snapshots
            if [ -n "''${2:-}" ]; then name "$2" && echo "entries changed in $2:" && direct -- diff "$2"; fi
            ;;
          --all) in_place all "''${2:-latest}" ;;
          "" | -*) usage ;;
          *)
            name "$1"
            stack=$1 snap=latest
            shift
            if [ -n "''${1:-}" ] && [ "$1" != --to ]; then snap=$1 && shift; fi
            if [ "''${1:-}" = --to ]; then
              [ -n "''${2:-}" ] || usage
              dir=$(realpath -m "$2")
              mkdir -p "$dir"
              direct -v "$dir:$dir" -- restore-to "$stack" "$snap" "$dir"
            else
              [ -z "''${1:-}" ] || usage
              in_place "$stack" "$snap"
            fi
            ;;
          esac
        '';
      })
    ];
  };
}
