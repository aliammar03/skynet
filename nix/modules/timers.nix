{ lib, ... }:
# The ops VM's scheduled units — skynet-nightly and skynet-deploy. `skynet` itself is a system
# package (flake.nix).
#
# The lab's other scheduled backups are NOT the ops VM's; they live in scripts/systemd/ for the
# hosts that install them:
#   skynet-restic-backup@  -> each docker host (root; reads /var/lib/docker/volumes)
#   skynet-pbs-gdrive      -> inside the PBS host.
#
# The repo lives in ~aliammar: Nix defines the host and its schedule, the checked-out repo is the
# replaceable runtime (system-design §4). Agent CLIs are home-manager packages (nix/home/).
let
  repo = "/home/aliammar/skynet";
  opsEnv = "/home/aliammar/.config/skynet-ops/ops.env";
  # Login-like env so the engine + git/gh creds in ~aliammar resolve. The agent CLIs are now
  # home-manager user packages → /etc/profiles/per-user/aliammar/bin (first on PATH).
  commonEnv = {
    HOME = "/home/aliammar";
    PATH = lib.mkForce "/etc/profiles/per-user/aliammar/bin:/run/current-system/sw/bin:/usr/bin:/bin";
  };
in
{
  # Operation record + write lock for every write path (src/skynet/writepath.py); persisted with
  # /opt/skynet-ops (impermanence.nix).
  systemd.tmpfiles.rules = [ "d /opt/skynet-ops/state 0750 aliammar users -" ];

  # The deploy loop: merge is the approval (ADR 0008); this applies each merged compose/<svc>/
  # revision that is not the one running, rolls a failure back to the last verified revision, and
  # holds a failed revision until main moves. A run still in progress skips the next tick.
  systemd.services.skynet-deploy = {
    description = "skynet deploy --pending (apply merged service revisions)";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    environment = commonEnv;
    serviceConfig = {
      Type = "oneshot";
      User = "aliammar";
      WorkingDirectory = repo;
      ExecStart = "/run/current-system/sw/bin/skynet deploy --pending --repo ${repo}";
      TimeoutStartSec = "60m";
    };
  };
  systemd.timers.skynet-deploy = {
    description = "Apply merged service revisions every 3 minutes";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "5m";
      OnUnitInactiveSec = "3m";
    };
  };

  systemd.services.skynet-nightly = {
    description = "skynet nightly maintenance (report-only)";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    environment = commonEnv;
    serviceConfig = {
      Type = "oneshot";
      User = "aliammar";
      WorkingDirectory = repo;
      EnvironmentFile = [ "-${opsEnv}" ]; # optional overrides; '-' = ok if absent
      ExecStart = "${repo}/bin/ops nightly";
      TimeoutStartSec = "30m";
      Nice = 10;
    };
  };
  systemd.timers.skynet-nightly = {
    description = "Nightly skynet maintenance (report-only)";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 03:30:00"; # between docker restic (02:30) and PBS sync (04:00)
      RandomizedDelaySec = "15m";
      Persistent = true;
    };
  };
}
