# ops: every morning, PBS's config against pbs/etc/ as deployed here from main (skynetv2.md → P4 →
# PBS's config in git). A difference goes to #alerts with the files' names; so does a failed check.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  # Every name PBS may keep in /etc/proxmox-backup that holds no secret. One that shows up on PBS
  # but not in git (a sync job added in the UI) is drift too. Never read: shadow.json,
  # token.shadow, tfa.json, keys and certificates, *-priv.cfg, remote.cfg, s3.cfg, metricserver.cfg.
  allow = [
    "acl.cfg"
    "datastore.cfg"
    "domains.cfg"
    "media-pool.cfg"
    "node.cfg"
    "notifications.cfg"
    "prune.cfg"
    "sync.cfg"
    "tape.cfg"
    "tape-job.cfg"
    "traffic-control.cfg"
    "user.cfg"
    "verification.cfg"
  ];
  want = ../pbs/etc;
  check = pkgs.writeShellApplication {
    name = "pbs-drift";
    runtimeInputs = with pkgs; [
      coreutils
      openssh
      gnutar
      diffutils
      findutils
      gnused
      jq
      curl
    ];
    text = ''
      post() {
        jq -n --arg c "$1" '{content: $c[0:1900]}' |
          curl -fsS -m 10 -H 'Content-Type: application/json' -d @- \
            -K <(printf 'url = "%s"\n' "$(cat "$CREDENTIALS_DIRECTORY/webhook")")
      }
      have=$(mktemp -d)
      trap 'rm -rf "$have"' EXIT
      # git's files, plus every allowlisted name whether git has it or not
      files=$({
        (cd ${want} && find . -type f)
        printf './proxmox-backup/%s\n' ${lib.escapeShellArgs allow}
      } | sort -u | tr '\n' ' ')
      if ! ssh -o BatchMode=yes -o ConnectTimeout=20 root@10.10.20.40 \
        "cd /etc && tar -c --ignore-failed-read $files 2>/dev/null" | tar -x -C "$have"; then
        post "**PBS** drift check failed: can't read its config over SSH (10.10.20.40)."
        exit 1
      fi
      if diff=$(diff -rq ${want} "$have"); then
        exit 0
      fi
      post "**PBS** config differs from \`pbs/etc/\` on main:
      $(printf '%s\n' "$diff" | sed -e 's|${want}|git|g' -e "s|$have|pbs|g")"
      exit 1
    '';
  };
in
{
  systemd.services.pbs-drift = {
    description = "Compare PBS's config with pbs/etc/ on main";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    startAt = "07:00"; # after the night's backups, prune and offsite start
    serviceConfig = {
      Type = "oneshot";
      User = "skynet"; # its key is root on PBS (D11); /etc/ssh/ssh_known_hosts pins PBS's
      LoadCredential = "webhook:${config.sops.secrets.discord_alerts_webhook.path}";
      ExecStart = lib.getExe check;
    };
  };
  systemd.timers.pbs-drift.timerConfig.Persistent = true;
}
