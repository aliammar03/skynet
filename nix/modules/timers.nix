{ lib, ... }:
# The ops VM's OWN scheduled units, declarative twins of scripts/systemd/*.
#
# Only two of the four scripts/systemd units run on THIS host (both User=ali):
#   skynet-nightly, skynet-cli-update.
# The other two run elsewhere and are NOT the ops VM's:
#   skynet-restic-backup@  -> each docker host (root; reads /var/lib/docker/volumes)
#   skynet-pbs-gdrive      -> inside the PBS host.
#
# The repo + agent CLIs live in ~aliammar (not the Nix store) by decision — Nix defines the host
# and its schedule; the checked-out repo is the replaceable runtime (system-design §4).
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

  systemd.services.skynet-cli-update = {
    description = "skynet weekly CLI update + model-suggestion refresh";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    environment = commonEnv;
    serviceConfig = {
      Type = "oneshot";
      User = "aliammar";
      WorkingDirectory = repo;
      ExecStart = "${repo}/scripts/update-clis.sh";
      TimeoutStartSec = "20m";
      Nice = 15;
    };
  };
  systemd.timers.skynet-cli-update = {
    description = "Weekly skynet CLI update + model-suggestion refresh";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "Sun *-*-* 05:00:00"; # after the nightly + PBS sync
      RandomizedDelaySec = "30m";
      Persistent = true;
    };
  };
}
