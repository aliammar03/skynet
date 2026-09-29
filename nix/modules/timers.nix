{ lib, ... }:
# The ops VM's scheduled units — skynet-deploy (30 s merge trigger), skynet-tofu (1 min Tofu
# apply-on-merge; defined but not enabled until its drills are recorded), skynet-watch (3 min health monitor), skynet-nightly, and the OnFailure alert. `skynet` itself is a system package (flake.nix).
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

  # The deploy loop: merge is the approval (ADR 0008). Every 30 s a `git ls-remote` asks whether
  # main moved; only then (or when the last pass is 15 min old) does the full pass run: apply each
  # merged compose/<svc>/ revision that is not the one running, roll a failure back to the last
  # verified revision, retire projects main no longer declares, and try the revert auto-merge gate
  # (AGENTS.md §3). No inbound path: nothing internet-facing reaches the ops VM.
  systemd.services.skynet-deploy = {
    description = "skynet deploy --pending --if-moved (apply merged service revisions)";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    onFailure = [ "skynet-alert@%n.service" ];
    environment = commonEnv;
    serviceConfig = {
      Type = "oneshot";
      User = "aliammar";
      WorkingDirectory = repo;
      ExecStart = "/run/current-system/sw/bin/skynet deploy --pending --if-moved --repo ${repo}";
      # --if-moved exits 0 for every outcome the pass records itself and 4 for rollback-failed
      # whose alert went out. A crash (Python exits 1), an alert that could not be sent (1),
      # unwritable trigger state (1), a timeout, or a kill fires OnFailure.
      SuccessExitStatus = [ 4 ];
      TimeoutStartSec = "60m";
    };
  };
  systemd.timers.skynet-deploy = {
    description = "Check for a merged main every 30 seconds";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "2m";
      OnUnitInactiveSec = "30s";
      AccuracySec = "5s";
    };
  };

  # OpenTofu under ADR 0008: each minute, apply every stack whose merged inputs are not the applied
  # ones and whose re-plan matches the PR's approved hash (src/skynet/tofu.py). Its own unit and its
  # own `tofu` lock, so an hours-long apply never delays a Docker deploy or a revert; an apply that
  # reboots docker-dmz can overlap a deploy there, which then rolls itself back.
  systemd.services.skynet-tofu = {
    description = "skynet tofu apply --pending (apply merged, hash-approved stacks)";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    onFailure = [ "skynet-alert@%n.service" ];
    environment = commonEnv;
    serviceConfig = {
      Type = "oneshot";
      User = "aliammar";
      WorkingDirectory = repo;
      ExecStart = "/run/current-system/sw/bin/skynet tofu apply --pending --repo ${repo}";
      # 0 for every outcome the pass records and alerts itself; 4 = rollback-failed whose alert
      # went out. A crash, an unsent alert, a timeout, or a kill fires OnFailure.
      SuccessExitStatus = [ 4 ];
      # = tofu.PASS_SECONDS: a stack starts only if its full worst case, apply plus rollback,
      # still fits (src/skynet/tofu.py); a test pins the two together.
      TimeoutStartSec = "5h";
    };
  };
  # NOT enabled: until the live LXC and VM rollback drills are recorded (SKY-025 P15), the executor
  # runs supervised (`skynet tofu apply --pending`, or `systemctl start skynet-tofu`). The promotion
  # PR that carries that evidence adds `wantedBy = [ "timers.target" ];` (a test pins this).
  systemd.timers.skynet-tofu = {
    description = "Apply merged OpenTofu stacks, checked every minute";
    wantedBy = [ ];
    timerConfig = {
      OnBootSec = "3m";
      OnUnitInactiveSec = "60s";
      AccuracySec = "5s";
    };
  };

  # The live health monitor (T1 read): verifies every deployed service, alerts on state change,
  # and pings the external dead-man's switch so a dead VM or timer still reaches the phone.
  systemd.services.skynet-watch = {
    description = "skynet watch (live service health)";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    onFailure = [ "skynet-alert@%n.service" ];
    environment = commonEnv;
    serviceConfig = {
      Type = "oneshot";
      User = "aliammar";
      WorkingDirectory = repo;
      ExecStart = "/run/current-system/sw/bin/skynet watch --repo ${repo}";
      # 1 = a service is unhealthy, 3 = monitor unavailable: both alert by state change. A run that
      # dies before its ping is caught by the dead-man's switch.
      SuccessExitStatus = [ 1 3 ];
      # A pass is bounded to well under one interval (src/skynet/watch.py); this is the backstop.
      TimeoutStartSec = "4m";
    };
  };
  # Passes START 3 min apart (OnUnitActiveSec, not OnUnitInactiveSec: a pass's own run time must
  # not stretch the gap). With two strikes and a bounded pass, an outage alerts in < 10 min; the
  # budget is in docs/design/observability.md.
  systemd.timers.skynet-watch = {
    description = "Verify every deployed service, passes starting 3 minutes apart";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "3m";
      OnUnitActiveSec = "3m";
      AccuracySec = "1s";
    };
  };

  # A skynet unit that crashed, timed out, or was killed pushes an alert (at most one an hour per
  # unit, so a crash loop is one message).
  systemd.services."skynet-alert@" = {
    description = "Alert that %i failed";
    environment = commonEnv;
    serviceConfig = {
      Type = "oneshot";
      User = "aliammar";
      ExecStart = "/run/current-system/sw/bin/skynet alert unit-failed %i";
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
