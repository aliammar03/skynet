# The merge window on ops (docs/plans/autonomy.md → Merges): the evening review, and the night's
# window with the programs it runs (skynet-merge, skynet-verify). A dry run until step 6: the window
# looks at every open PR, logs what it would merge and how every stack and host is, and merges
# nothing. The review is real, on real PRs. This file and the window's programs stand in for Ali's
# review, so they're code-owned (.github/CODEOWNERS).
{
  config,
  lib,
  pkgs,
  ...
}:
let
  repo = "/home/skynet/skynet";
  state = "/var/lib/skynet-window";
  # The bot's token, for gh alone: nothing else these programs run sees it.
  ghEnv = config.sops.templates."agent.env".path;
  # Review runs an evening: they share Ali's Claude plan with the incident runs.
  budget = 6;
  logs = "https://logs.aliammar.net";
  kv = attrs: lib.concatStringsSep " " (lib.mapAttrsToList (k: v: "${k}=${v}") attrs);
  # The hosts the agent SSHes into (agent.nix's known hosts), as whom: root on PBS, skynet elsewhere
  # (with sudo where ADR-0011 makes it root). ops runs its own checks locally.
  hosts =
    lib.mapAttrs (
      n: k: "${if n == "pbs" then "root" else "skynet"}@${lib.head k.hostNames}"
    ) config.programs.ssh.knownHosts
    // {
      ops = "local";
    };
  # doco-cd's targets, and the Docker host each deploys to.
  targets = {
    admin = "docker-admin";
    dmz = "docker-dmz";
  };

  verify = pkgs.callPackage ../packages/skynet-verify {
    runtimeEnv = {
      REPO = repo;
      HOSTS = kv hosts;
      TARGETS = kv targets;
      # What ops reads without a login (stacks/admin/authelia/configuration.yml).
      GATUS = "https://status.aliammar.net";
      METRICS = "https://metrics.aliammar.net";
      LOGS = logs;
    };
  };
  merge = pkgs.callPackage ../packages/skynet-merge {
    skynet-verify = verify;
    runtimeEnv = {
      REPO = repo;
      GH_ENV = ghEnv;
      STATE = state;
      LOGS = logs;
      # A Renovate PR's newest commit, at least 3 days old (renovate.json says why).
      AGE = toString (3 * 86400);
    };
  };
  window = pkgs.callPackage ../packages/skynet-window {
    skynet-merge = merge;
    skynet-verify = verify;
    runtimeEnv = {
      STATE = state;
      GH_ENV = ghEnv;
    };
  };

  # `skynet-review`, each evening: the open PRs the window could take (Renovate's and the agent's,
  # tier A or B) with no review on their newest commit, oldest first, up to the budget. For each, the
  # stack's new images are pulled on its host first, so the window's deploy only switches and an
  # image that won't pull is in the data. Then one run of runbooks/review.md (`skynet-run`, with the
  # web), whose answer goes on the PR, marked with the commit it read and its first line's verdict.
  # `ali` labels the PR tier:C, `steps` labels it steps. By hand, as skynet: `skynet-review <pr>`
  # reviews that one now (outside the budget); `DRY_RUN=1` prints the review instead of posting it.
  review = pkgs.writeShellApplication {
    name = "skynet-review";
    runtimeInputs = with pkgs; [
      coreutils
      gh
      git
      gnused
      jq
      openssh
      merge
    ];
    text = ''
      repo=aliammar03/skynet
      ghx() { (
        set -a
        # shellcheck disable=SC1091 # rendered by sops-nix
        . ${ghEnv}
        gh "$@"
      ); }
      git -C ${repo} fetch -q origin || true
      if [ "$#" -gt 0 ]; then
        [[ $1 =~ ^[0-9]+$ ]] || { echo "usage: skynet-review [<pr>]" >&2; exit 2; }
        prs=("$1") budget=1
      else
        mapfile -t prs < <(ghx pr list --repo "$repo" --state open --limit 100 --json number,createdAt,author,isDraft \
          --jq '[.[] | select((.isDraft | not) and (.author.login == "app/renovate" or .author.login == "aliammar-skynet"))]
            | sort_by(.createdAt) | .[].number')
        budget=${toString budget}
      fi
      runs=0
      for n in "''${prs[@]}"; do
        [ "$runs" -lt "$budget" ] || break
        j=$(ghx pr view "$n" --repo "$repo" --json number,title,url,headRefOid,author,labels,files,body,comments)
        sha=$(jq -r .headRefOid <<<"$j")
        if jq -e --arg m "<!-- skynet-review $sha " 'any(.comments[]; .author.login == "aliammar-skynet" and (.body | contains($m)))' \
          <<<"$j" >/dev/null; then
          continue
        fi
        read -r tier stack <<<"$(skynet-merge --tier "$n")"
        case "$tier" in A | B) ;; *) continue ;; esac
        diff=$(ghx pr diff "$n" --repo "$repo")
        pulls=
        if [ "$tier" = A ]; then
          case "''${stack%%/*}" in
          admin) dest=${hosts.docker-admin} ;;
          *) dest=${hosts.docker-dmz} ;;
          esac
          while IFS= read -r img; do
            if ssh -n -o BatchMode=yes -o ConnectTimeout=15 "$dest" "sudo docker pull -q $img" >/dev/null 2>&1; then
              pulls+="$img: pulled on ''${dest#*@}"$'\n'
            else
              pulls+="$img: did NOT pull on ''${dest#*@}"$'\n'
            fi
          done < <(sed -nE 's/^\+ +image: *([^ ]+@sha256:[0-9a-f]{64}).*/\1/p' <<<"$diff")
        fi
        runs=$((runs + 1))
        out=$({
          jq -r '"PR #\(.number): \(.title)\n\(.url)\nby \(.author.login); newest commit \(.headRefOid); labels: \([.labels[].name] | join(", "))"' <<<"$j"
          echo "tier: $tier ''${stack:-}"
          printf '\n## Files\n'
          jq -r '.files[].path' <<<"$j"
          printf '\n## Its new images on their host\n%s\n' "''${pulls:-none to pull}"
          printf '\n## The diff (up to 20,000 characters)\n%s\n' "''${diff:0:20000}"
          printf '\n## The PR body (up to 15,000 characters; Renovate puts the release notes here)\n'
          jq -r '.body[:15000]' <<<"$j"
        } | DRY_RUN=1 skynet-run review "Review of #$n" web) || true
        verdict=$(sed -nE '1,3{s/^[*_ ]*Verdict[*_ ]*:?[*_ ]* *(merge|hold|steps|ali)\b.*/\1/p}' <<<"$out" | head -n 1)
        if [ -z "$verdict" ]; then
          echo "skynet-review: #$n: the run gave no verdict, so no review; it's tried again next evening" >&2
          continue
        fi
        # shellcheck disable=SC2016 # Markdown's backticks, not a command
        body=$(printf '<!-- skynet-review %s %s -->\n**Evening review** of %s (`runbooks/review.md`, a run that didn'"'"'t write the PR)\n\n%s\n' \
          "$sha" "$verdict" "''${sha:0:7}" "$out")
        if [ -n "''${DRY_RUN:-}" ]; then
          printf '%s\n' "$body"
          continue
        fi
        ghx pr comment "$n" --repo "$repo" --body-file - <<<"$body"
        case "$verdict" in
        ali) ghx api -X POST "repos/$repo/issues/$n/labels" -f "labels[]=tier:C" >/dev/null ;;
        steps) ghx api -X POST "repos/$repo/issues/$n/labels" -f "labels[]=steps" >/dev/null ;;
        esac
        echo "skynet-review: #$n ''${sha:0:7}: $verdict"
      done
    '';
  };

  unit = description: script: {
    inherit description;
    wants = [ "network-online.target" ];
    after = [
      "network-online.target"
      "skynet-clone.service"
    ];
    # The host's packages, `claude` and `skynet-run` among them, as in the agent's sessions.
    environment.PATH = lib.mkForce "/run/wrappers/bin:/run/current-system/sw/bin";
    serviceConfig = {
      Type = "oneshot";
      User = "skynet";
      StateDirectory = "skynet-window";
      ExecStart = lib.getExe script;
    };
  };
in
{
  # Renovate writes its PRs on Mondays before 06:00; a review needs one evening, and a Renovate PR
  # three days, so the week's updates go out from Thursday's window.
  systemd.services.skynet-review = unit "The evening review of the PRs the window could take" review // {
    startAt = "*-*-* 19:00:00";
  };
  # After the night's snapshots (04:20), backups (04:30) and Unraid's undo copies (04:00, done by
  # about 04:25), while nobody uses the apps.
  systemd.services.skynet-window = unit "The night's merge window (a dry run: it merges nothing)" window // {
    startAt = "*-*-* 05:00:00";
  };

  # By hand too, as skynet: `skynet-verify all`, `skynet-merge <pr>`, `skynet-window`.
  environment.systemPackages = [
    verify
    merge
    window
    review
  ];
}
