# Docker hosts (docker-admin, docker-dmz): Docker, the networks stacks join (stacks never create
# networks; skynetv2.md → Conventions → Networks), doco-cd, which deploys `stacks/<target>/` from
# `main`, with Apprise for its Discord notices, and cAdvisor (P5).
{
  config,
  lib,
  pkgs,
  inputs,
  ...
}:
let
  inherit (config.skynet.docker)
    macvlan
    doorNetworks
    docoTarget
    appdataSnapshots
    ;
  creds = "/run/doco-cd"; # what doco-cd may read: its age key, API secret, Apprise URL
  # Same path inside and out, so stacks' relative bind mounts resolve. Holds doco-cd's checkout, with
  # the files this host can decrypt decrypted (root-only, like /run/secrets).
  data = "/var/lib/doco-cd";
  # docker-dmz's btrfs top level (hosts/docker-dmz/disk.nix): @appdata (/opt/appdata), @snapshots.
  pool = "/mnt/appdata-pool";
  unstable = inputs.nixpkgs-unstable.legacyPackages.${pkgs.stdenv.hostPlatform.system};

  # btrbk-appdata's hooks, as root. The stamp tells the backup job how old the snapshot it mounts is;
  # `latest` is the snapshot it mounts. The metric is the stamp of the newest good snapshot, for
  # node-exporter's textfile collector (modules/observability.nix).
  appdataStamp = pkgs.writeShellApplication {
    name = "appdata-stamp";
    runtimeInputs = [ pkgs.coreutils ];
    text = "date +%s >/opt/appdata/.snapshot-stamp";
  };
  appdataLatest = pkgs.writeShellApplication {
    name = "appdata-latest";
    runtimeInputs = [
      pkgs.coreutils
      pkgs.findutils
    ];
    text = ''
      cd ${pool}/@snapshots
      newest=$(find . -mindepth 1 -maxdepth 1 -name '@appdata.*' -printf '%f\n' | sort | tail -n 1)
      [ -n "$newest" ] || { echo "appdata-latest: no snapshot" >&2; exit 1; }
      # A real folder by that name (Docker makes one for a missing bind source) would swallow it.
      if [ -e latest ] && [ ! -L latest ]; then echo "appdata-latest: latest isn't a link" >&2; exit 1; fi
      ln -sfn "$newest" latest
      umask 022
      prom=/var/lib/node-exporter/appdata-snapshot.prom
      printf '%s\n' \
        '# HELP skynet_appdata_snapshot_timestamp_seconds When btrbk took the newest snapshot of /opt/appdata.' \
        '# TYPE skynet_appdata_snapshot_timestamp_seconds gauge' \
        "skynet_appdata_snapshot_timestamp_seconds $(cat /opt/appdata/.snapshot-stamp)" >"$prom.tmp"
      mv "$prom.tmp" "$prom"
    '';
  };

  # Restores, from a local snapshot or from Drive (skynetv2.md → P4 → Restores).
  skynetRestore = pkgs.writeShellApplication {
    name = "skynet-restore";
    runtimeInputs = [
      config.virtualisation.docker.package
      unstable.restic # the backup image's version (0.19)
      pkgs.rclone
      pkgs.rsync
      pkgs.coreutils
      pkgs.findutils
      pkgs.gnugrep
      pkgs.gnused
      pkgs.util-linux # flock
      pkgs.systemd
    ];
    runtimeEnv = {
      REPO = "rclone:gdrive:skynet/restic/${config.networking.hostName}";
      EXCLUDES = "${../stacks/${docoTarget}/backup/excludes.txt}";
      SNAPSHOTS = lib.optionalString appdataSnapshots "${pool}/@snapshots";
      ENV_FILE = config.sops.secrets.restic-appdata-env.path;
      RCLONE_FILE = config.sops.secrets.restic-appdata-rclone.path;
    };
    text = builtins.readFile ./skynet-restore.sh;
  };
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

  options.skynet.docker.appdataSnapshots = lib.mkEnableOption ''
    btrbk's snapshots of /opt/appdata, a btrfs subvolume under ${pool}: the backup job copies the
    newest, and skynet-restore restores from any'';

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
        })
      // {
        # The backup stack's own secrets, for skynet-restore on the host. sops-nix renders dotenv and
        # INI files whole (it ignores `key`).
        restic-appdata-env = {
          sopsFile = ../stacks/${docoTarget}/backup/secret.sops.env;
          format = "dotenv";
        };
        restic-appdata-rclone = {
          sopsFile = ../stacks/${docoTarget}/backup/rclone.sops.conf;
          format = "ini";
        };
      };
    systemd.tmpfiles.rules = [
      "d ${data} 0700 root root -"
      # restic's caches, on ext4: the backup job's (its /cache) and skynet-restore's.
      "d /var/cache/restic-appdata 0700 root root -"
      "d /var/cache/skynet-restore 0700 root root -"
    ];

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
    # doco-cd starts only once /opt/appdata holds the host's data: `skynet-restore … --all` writes
    # the marker last, or a hand release does (runbooks/new-vm.md, step 6). A fresh install's
    # /opt/appdata is empty, and so is a wiped data disk's, so no app starts on nothing. A restore
    # in place takes the marker away while it works, so not even a switch or a reboot starts
    # doco-cd under it.
    systemd.services.docker-doco-cd.unitConfig = {
      ConditionPathExists = "/opt/appdata/.data-ready";
      RequiresMountsFor = "/opt/appdata";
    };
    # The doco-cd API and MCP answer only to ops (OPNsense must allow it too).
    networking.firewall.extraCommands = ''
      iptables -A nixos-fw -p tcp -s 10.10.90.91 --dport 8080 -j nixos-fw-accept
    '';

    # cAdvisor: CPU, memory, network and disk I/O per container, for docker-admin's VictoriaMetrics.
    # On the host, not in a stack: it reads every cgroup and Docker's containerd as root. Docker 29
    # keeps images in containerd's snapshotter, which cAdvisor reads through Docker's own containerd
    # (its default socket is a standalone containerd's, and without it no container has a name).
    services.cadvisor = {
      enable = true;
      listenAddress = "0.0.0.0"; # the firewall admits only docker-admin (observability.nix)
      port = 9338; # 8080 is doco-cd's
      extraOptions = [
        "-containerd=/run/docker/containerd/containerd.sock"
        "-docker_only=true"
        # The compose project as the one label, not every container label (fewer series).
        "-store_container_labels=false"
        "-whitelisted_container_labels=com.docker.compose.project"
        "-enable_metrics=cpu,memory,network,diskIO,oom_event"
        "-housekeeping_interval=15s"
      ];
    };
    skynet.metricsPorts = [
      9338 # cAdvisor
      9120 # doco-cd's metrics
    ];

    # `skynet-restore`: a stack's data back from a local snapshot or from Drive, with doco-cd paused
    # (stacks/<target>/backup/README.md).
    environment.systemPackages = [ skynetRestore ];

    # btrbk (appdataSnapshots): a read-only snapshot of @appdata at 04:20, which the backup job copies
    # at 04:30. Every snapshot is kept for 2 days, then one a day for 7; btrbk always keeps the
    # newest.
    services.btrbk.instances = lib.mkIf appdataSnapshots {
      appdata = {
        onCalendar = "*-*-* 04:20:00";
        snapshotOnly = true;
        settings = {
          snapshot_preserve_min = "2d";
          snapshot_preserve = "7d";
          volume.${pool} = {
            snapshot_dir = "@snapshots";
            subvolume."@appdata" = { };
          };
        };
      };
    };
    # The module allows 10 minutes of slack; the snapshot must come before the backup.
    systemd.timers.btrbk-appdata = lib.mkIf appdataSnapshots {
      timerConfig.AccuracySec = lib.mkForce "1min";
    };
    # As root (`+`), since btrbk runs as user btrbk.
    systemd.services.btrbk-appdata = lib.mkIf appdataSnapshots {
      serviceConfig = {
        ExecStartPre = "+${lib.getExe appdataStamp}";
        ExecStartPost = "+${lib.getExe appdataLatest}";
      };
    };
  };
}
