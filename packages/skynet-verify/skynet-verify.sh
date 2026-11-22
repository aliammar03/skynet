# skynet-verify: whether a stack or a host is well, from evidence the agent didn't write
# (docs/plans/autonomy.md → Verify and roll back). It reads Docker on the stack's host (the agent's
# key and sudo, ADR-0011), Gatus, VictoriaLogs, VictoriaMetrics, doco-cd's metrics and the repo at
# the commit it verifies; it prints each check's evidence and exits 0 only when every check passes.
# A container's environment holds secrets, so only the fields it checks leave a host.
# modules/window.nix sets REPO (the agent's clone), HOSTS ("<host>=<user>@<ip> …"), TARGETS
# ("<doco target>=<host> …"), and GATUS, METRICS and LOGS: the URLs ops reads without a login.

usage() {
  cat >&2 <<'EOF'
usage: skynet-verify stack <target>/<stack> [--ref <commit>] [--since <epoch>] [--watch <seconds>]
       skynet-verify stack <target>/<stack> --now
       skynet-verify host <host> [--deployed <commit>]
       skynet-verify all
stack: after a change: deployed at the commit (default main), running and healthy, then steady for
       --watch seconds (default 300); its Gatus rows green on results since --since (default 10
       minutes ago); its error lines near yesterday's; its smoke check passing. A job: doco-cd
       ran it in the last 26 hours, and no run failed. --now: as main has it, without waiting.
host:  comin's last fetch, build and deploy (at --deployed's commit, when given), no failed unit,
       every scrape target up; on ops also the agent's sessions, a headless claude and SSH.
all:   every stack on main and every host as they are now, without waiting.
EOF
  exit 2
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
red=0 # failed checks of the current stack or host
pass() { printf '  ok    %s\n' "$*"; }
fail() {
  printf '  FAIL  %s\n' "$*"
  red=$((red + 1))
}
now() { date +%s; }
iso() { date -u -d "@$1" +%FT%TZ; }

lookup() { # <key> <"k=v …">: the key's value
  local kv
  for kv in $2; do
    if [ "${kv%%=*}" = "$1" ]; then
      echo "${kv#*=}"
      return 0
    fi
  done
  return 1
}
on() { # <host> <command>: run there as the agent (`local`: ops itself)
  local dest
  dest=$(lookup "$1" "$HOSTS") || return 1
  if [ "$dest" = local ]; then
    bash -c "$2"
  else
    ssh -n -o BatchMode=yes -o ConnectTimeout=15 "$dest" "$2"
  fi
}
promql() { curl -fsS --max-time 30 "$METRICS/api/v1/query" --data-urlencode "query=$1" | jq -c '.data.result'; }
# The sum of a PromQL query's values, 0 when it has none.
promsum() { promql "$1" | jq -r '[.[].value[1] | tonumber] | add // 0 | floor'; }
logcount() { # <LogsQL filter>: how many lines match
  curl -fsS --max-time 60 "$LOGS/select/logsql/query" --data-urlencode "query=$1 | stats count() as n" |
    jq -r '.n // "0"' | head -n 1
}
gatus() { # every endpoint's results: name, then each result's time (epoch) and outcome
  curl -fsS --max-time 30 "$GATUS/api/v1/endpoints/statuses?page=1&pageSize=20" |
    jq -c '[.[] | {name, results: [.results[] | {t: (.timestamp | sub("\\.[0-9]+"; "") | fromdateiso8601), ok: .success}]}]'
}

# <host> <project>: its containers (jobs' stopped ones too), trimmed on the host itself
containers() {
  local out
  out=$(on "$1" "sudo docker ps -aq --filter label=com.docker.compose.project=$2 | xargs -r sudo docker inspect | jq -c '[.[] | {name: (.Name | ltrimstr(\"/\")), id: .Id, image: .Config.Image, status: .State.Status, health: (.State.Health.Status // \"none\"), restarts: .RestartCount, started: .State.StartedAt, finished: .State.FinishedAt, exit: .State.ExitCode}]'") || return 1
  echo "${out:-[]}"
}

# <compose json>: each service's container, its image ("" when built here), whether it's a job,
# and whether it says it has no healthcheck
services() {
  jq -c '[.services // {} | to_entries[] | .value | {c: .container_name, i: (if .build then "" else (.image // "") end),
    job: ((.labels // {}) | if type == "array" then any(.[]; test("^cd\\.doco\\.job\\.enabled=\"?true"))
      else ((."cd.doco.job.enabled" // "") | tostring) == "true" end),
    nocheck: ((."x-no-healthcheck" // "") | length > 0)}]' <<<"$1"
}

# <services> <containers> [<containers at the watch's start>] [<recent: epoch>]: what's wrong with
# the long-running ones, a line each. With the start's containers, a new container or restart count
# is a restart; with <recent>, a restart counted since then is.
problems() {
  jq -r --argjson svcs "$1" --argjson first "${3:-null}" --argjson recent "${4:-null}" '
    (map({key: .name, value: .}) | from_entries) as $c
    | (if $first == null then null else ($first | map({key: .name, value: .}) | from_entries) end) as $f
    | $svcs[] | select(.job | not) | .c as $n | $c[$n] as $x
    | if $x == null then "\($n): no container"
      elif $x.status != "running" then "\($n): \($x.status)"
      elif $x.health == "none" and (.nocheck | not) then "\($n): Docker checks no health, and the service has no x-no-healthcheck"
      elif $x.health != "none" and $x.health != "healthy" then "\($n): \($x.health)"
      elif $f != null and (($f[$n].id // "") != $x.id or ($f[$n].restarts // -1) != $x.restarts) then "\($n): restarted during the watch"
      elif $recent != null and $x.restarts > 0 and ($x.started | sub("\\.[0-9]+"; "") | fromdateiso8601) > $recent
        then "\($n): restarted at \($x.started[:19])Z (\($x.restarts) restarts)"
      else empty end' <<<"$2"
}

# <target> <stack> <sha> <services>: the Gatus rows that watch the stack, a line each: those whose
# URL's host is a door site's that routes to one of its containers (every site of a door, for the
# door), or, on docker-admin, where Gatus runs, one of its containers itself; and a job's
# healthchecks.io row, named "<host> <stack>" or "<stack>"
rows_of() {
  local t=$1 s=$2 sha=$3 names keys f site door ups g group name url h host
  names=$(jq -r '.[].c' <<<"$4")
  keys=
  while IFS= read -r f; do
    site=$(git -C "$REPO" show "$sha:$f")
    door=${f#stacks/"$t"/}
    door=${door%%/*}
    ups=$(sed -nE 's#^\s*reverse_proxy\s+(https?://)?([^:/ {]+).*#\2#p' <<<"$site")
    if [ "$door" = "$s" ] || grep -qxF -f <(printf '%s\n' "$names") <<<"$ups"; then
      keys="$keys $(sed -nE 's#^@[^ ]+ host (.+)$#\1#p' <<<"$site" | tr '\n' ' ')"
    fi
  done < <(git -C "$REPO" ls-tree -r --name-only "$sha" -- "stacks/$t/" | grep -E "^stacks/$t/caddy-[^/]+/conf/sites/[^/]+\.conf$" || true)
  if [ "$t" = admin ]; then keys="$keys $(tr '\n' ' ' <<<"$names")"; fi
  host=$(lookup "$t" "$TARGETS") || host=
  while IFS= read -r g; do
    git -C "$REPO" show "$sha:$g" | yq -o=json 'explode(.)' 2>/dev/null | jq -r '(.endpoints // [])[] | [(.group // "-"), .name, .url] | @tsv'
  done < <(git -C "$REPO" ls-tree --name-only "$sha" -- stacks/admin/gatus/config/) |
    while IFS=$'\t' read -r group name url; do
      h=$(sed -E 's#^[a-z]+://##; s#[:/].*$##' <<<"$url")
      if [ "$group" = job ] && { [ "$name" = "$host $s" ] || [ "$name" = "$s" ]; }; then
        printf '%s\n' "$name"
      else
        case " $keys " in *" $h "*) printf '%s\n' "$name" ;; esac
      fi
    done
}

# <target> <stack> <sha> <since> <watch> <live: 1|"">
verify_stack() {
  local t=$1 s=$2 sha=$3 since=$4 watch=$5 live=$6
  local host compose svcs ins wrong deadline first bad rows rs res c runs errs deploys from to after before out names
  red=0
  echo "== $t/$s at ${sha:0:7}"
  if ! host=$(lookup "$t" "$TARGETS"); then
    fail "no Docker host for target $t"
    return 1
  fi
  if ! compose=$(git -C "$REPO" show "$sha:stacks/$t/$s/compose.yaml" 2>/dev/null | yq -o=json 'explode(.)' 2>/dev/null); then
    fail "stacks/$t/$s has no compose.yaml at ${sha:0:7}"
    return 1
  fi
  svcs=$(services "$compose")

  # Deployed: each service's container runs the image the commit names. After a change doco-cd has
  # up to 10 minutes (a poll a minute, then the pulls).
  deadline=$(now)
  [ -n "$live" ] || deadline=$((deadline + ${VERIFY_DEPLOY_WAIT:-600}))
  while :; do
    ins=$(containers "$host" "$s") || ins=
    if [ -n "$ins" ]; then
      wrong=$(jq -r --argjson svcs "$svcs" '(map({key: .name, value: .image}) | from_entries) as $c
        | $svcs[] | select(.i != "" and $c[.c] != .i) | "\(.c) runs \($c[.c] // "nothing")"' <<<"$ins")
      [ -n "$wrong" ] || break
    else
      wrong="can't read its containers on $host"
    fi
    [ "$(now)" -lt "$deadline" ] || break
    sleep 15
  done
  if [ -n "$wrong" ]; then
    fail "deployed: not as ${sha:0:7} names: $(paste -sd';' <<<"$wrong")"
    return 1
  fi
  pass "deployed: $(jq length <<<"$svcs") services on the images ${sha:0:7} names"
  if [ -z "$live" ]; then
    deploys=$(promsum "increase(doco_cd_deployments_total{instance=\"$host\",deployment=\"$s\"}[$(($(now) - since + 60))s])") || deploys='?'
    errs=$(promsum "increase(doco_cd_deployment_errors_total{instance=\"$host\",deployment=\"$s\"}[$(($(now) - since + 60))s])") || errs='?'
    if [ "$errs" = 0 ]; then
      pass "doco-cd: $deploys deploys of $s since $(iso "$since"), none failed"
    else
      fail "doco-cd: $errs failed deploys of $s since $(iso "$since")"
    fi
  fi

  # Running and healthy (after a change, once each check has had its start: up to 5 minutes), then
  # steady: the same containers, healthy, no restart, for the whole watch.
  if [ -n "$(jq -r '.[] | select(.job | not) | .c' <<<"$svcs")" ]; then
    deadline=$(now)
    [ -n "$live" ] || deadline=$((deadline + ${VERIFY_HEALTHY_WAIT:-300}))
    while :; do
      ins=$(containers "$host" "$s") || ins='[]'
      if [ -n "$live" ]; then
        bad=$(problems "$svcs" "$ins" null "$(($(now) - 900))")
      else
        bad=$(problems "$svcs" "$ins")
      fi
      [ -n "$bad" ] || break
      [ "$(now)" -lt "$deadline" ] || break
      sleep 15
    done
    if [ -n "$bad" ]; then
      fail "healthy: $(paste -sd';' <<<"$bad")"
    elif [ "$watch" -gt 0 ]; then
      first=$ins
      deadline=$(($(now) + watch))
      while [ "$(now)" -lt "$deadline" ]; do
        sleep 20
        ins=$(containers "$host" "$s") || ins='[]'
        bad=$(problems "$svcs" "$ins" "$first")
        [ -z "$bad" ] || break
      done
      if [ -n "$bad" ]; then fail "steady: $(paste -sd';' <<<"$bad")"; else pass "steady: running and healthy for ${watch}s, no restart"; fi
    elif [ -n "$live" ]; then
      pass "healthy: every long-running container running, none restarted in 15 minutes"
    else
      pass "healthy: every long-running container running"
    fi
  fi

  # Jobs: doco-cd's runs of each in the last 26 hours, none failed. A one-off run is a container of
  # its own, gone after, so doco-cd's counters say how it went.
  for c in $(jq -r '.[] | select(.job) | .c' <<<"$svcs"); do
    runs=$(promsum "increase(doco_cd_scheduled_runs_total{instance=\"$host\",stack=\"$s\",exported_job=\"$c\"}[26h])") || runs='?'
    errs=$(promsum "increase(doco_cd_scheduled_run_errors_total{instance=\"$host\",stack=\"$s\",exported_job=\"$c\"}[26h])") || errs='?'
    if [ "$errs" = 0 ]; then pass "job $c: $runs runs in 26 hours, none failed"; else fail "job $c: $errs of $runs runs in 26 hours failed"; fi
  done

  # Gatus: each row that watches the stack is green on every result since (a 5-minute row has had
  # one by the end of the watch; it gets 6 minutes more).
  rows=$(rows_of "$t" "$s" "$sha" "$svcs")
  if [ -n "$rows" ]; then
    rs=$(jq -R . <<<"$rows" | jq -sc .)
    deadline=$(now)
    [ -n "$live" ] || deadline=$((deadline + ${VERIFY_ROWS_WAIT:-360}))
    while :; do
      if res=$(gatus); then
        if [ -n "$live" ]; then
          bad=$(jq -r --argjson rs "$rs" '.[] | select(.name as $n | $rs | index($n)) | (.results[-1] // {ok: false}) as $r
            | select($r.ok | not) | "\(.name) failing"' <<<"$res")
        else
          bad=$(jq -r --argjson rs "$rs" --argjson since "$since" '.[] | select(.name as $n | $rs | index($n))
            | [.results[] | select(.t > $since)] as $new
            | if ($new | length) == 0 then "\(.name): no result yet" elif any($new[]; .ok | not) then "\(.name) failed" else empty end' <<<"$res")
        fi
      else
        bad="can't read Gatus"
      fi
      [ -n "$bad" ] || break
      [ "$(now)" -lt "$deadline" ] || break
      sleep 30
    done
    if [ -n "$bad" ]; then fail "gatus: $(paste -sd';' <<<"$bad")"; else pass "gatus: green: $(paste -sd',' <<<"$rows")"; fi
  elif [ "$s" = gatus ]; then
    # Gatus itself has no healthcheck (its image is only the binary): its API answering is the check.
    if gatus >/dev/null; then pass "gatus: its API answers"; else fail "gatus: its API doesn't answer"; fi
  else
    pass "gatus: no row watches it (its containers' health stands for it)"
  fi

  # Error lines: the containers' lines naming an error, a fatal or a panic, against the same span a
  # day before. Not well above (3 times, plus 10) passes.
  from=$since to=$(now)
  [ -z "$live" ] || from=$((to - 900))
  names=$(jq -r '[.[].c | "\"\(.)\""] | join(",")' <<<"$svcs")
  if after=$(logcount "_time:[$(iso "$from"), $(iso "$to")] _HOSTNAME:=$host CONTAINER_NAME:in($names) (i(error*) OR i(fatal*) OR i(panic*))") &&
    before=$(logcount "_time:[$(iso $((from - 86400))), $(iso $((to - 86400)))] _HOSTNAME:=$host CONTAINER_NAME:in($names) (i(error*) OR i(fatal*) OR i(panic*))"); then
    if [ "$after" -le $((3 * before + 10)) ]; then
      pass "errors: $after lines since $(iso "$from"), $before in the same span yesterday"
    else
      fail "errors: $after lines since $(iso "$from"), against $before in the same span yesterday"
    fi
  else
    fail "errors: can't read VictoriaLogs"
  fi

  # Its smoke check, where a health endpoint doesn't show use (stacks/README.md → The folder).
  if git -C "$REPO" cat-file -e "$sha:stacks/$t/$s/smoke.sh" 2>/dev/null; then
    git -C "$REPO" show "$sha:stacks/$t/$s/smoke.sh" >"$tmp/smoke.sh"
    if out=$(timeout 120 bash "$tmp/smoke.sh" 2>&1); then
      pass "smoke: $(tail -n 1 <<<"$out")"
    else
      fail "smoke: $(tail -n 2 <<<"$out" | paste -sd' ')"
    fi
  fi
  [ "$red" = 0 ]
}

# <host> [<sha>]
verify_host() {
  local h=$1 sha=${2:-} r flags units down
  red=0
  echo "== host $h"
  if on "$h" true; then pass "ssh: answers"; else fail "ssh: no answer"; fi
  r=$(promql "comin_deployment_info{instance=\"$h\"}") || r=
  if [ -n "$r" ] && [ "$r" != "[]" ]; then
    flags=$(promql "{__name__=~\"comin_last_(fetch|eval|build|deployment)_failed\",instance=\"$h\"} == 1" |
      jq -r '[.[].metric.__name__ | sub("comin_last_"; "") | sub("_failed"; "")] | join(",")') || flags='?'
    if [ -n "$flags" ]; then fail "comin: last $flags failed"; else pass "comin: fetch, eval, build and deploy ok"; fi
    r=$(jq -r '.[0].metric | "\(.status) \(.commit_id)"' <<<"$r")
    if [ "${r%% *}" != "done" ]; then
      fail "comin: last deployment ${r%% *}"
    elif [ -n "$sha" ] && [ "${r#* }" != "$sha" ]; then
      fail "comin: deployed ${r#* }, not $sha"
    else
      pass "comin: deployed ${r#* }"
    fi
  fi
  units=$(promql "node_systemd_unit_state{instance=\"$h\",state=\"failed\"} == 1" | jq -r '[.[].metric.name] | join(",")') || units='?'
  if [ -z "$units" ]; then pass "units: none failed"; else fail "units: failed: $units"; fi
  down=$(promql "up{instance=\"$h\"} == 0" | jq -r '[.[].metric.job] | join(",")') || down='?'
  if [ -z "$down" ]; then pass "scrape: every target up"; else fail "scrape: down: $down"; fi
  if [ "$h" = ops ]; then
    if systemctl is-active --quiet skynet-agent skynet-spawn; then pass "sessions: skynet-agent and skynet-spawn active"; else fail "sessions: $(systemctl is-active skynet-agent skynet-spawn | paste -sd' ')"; fi
    # As bare as skynet-run's runs: no settings (so no plugins: not the Discord one), no MCP server,
    # no tool.
    if timeout 120 claude -p --restricted --strict-mcp-config --mcp-config '{"mcpServers":{}}' --tools "" \
      --no-session-persistence 'Reply with the one word: ready' 2>/dev/null | grep -qi ready; then
      pass "claude: a headless run answers"
    else
      fail "claude: a headless run doesn't answer"
    fi
    for r in $HOSTS; do
      if on "${r%%=*}" true; then :; else fail "ssh: ${r%%=*} doesn't answer"; fi
    done
  fi
  [ "$red" = 0 ]
}

mode=${1:-}
[ "$#" -gt 0 ] && shift
git -C "$REPO" fetch -q origin 2>/dev/null || true
case "$mode" in
stack)
  [[ ${1:-} =~ ^([a-z]+)/([a-z0-9][a-z0-9-]*)$ ]] || usage
  t=${BASH_REMATCH[1]} s=${BASH_REMATCH[2]}
  shift
  ref=origin/main since=$(($(now) - 600)) watch=300 live=
  while [ "$#" -gt 0 ]; do
    case "$1" in
    --ref) ref=${2:?} && shift 2 ;;
    --since) since=${2:?} && shift 2 ;;
    --watch) watch=${2:?} && shift 2 ;;
    --now) live=1 since=$(($(now) - 900)) && shift ;;
    *) usage ;;
    esac
  done
  [[ $since =~ ^[0-9]+$ && $watch =~ ^[0-9]+$ ]] || usage
  sha=$(git -C "$REPO" rev-parse --verify --quiet "$ref^{commit}") || {
    echo "skynet-verify: no commit $ref" >&2
    exit 2
  }
  if verify_stack "$t" "$s" "$sha" "$since" "$watch" "$live"; then echo "verified $t/$s: green"; else
    echo "verified $t/$s: red"
    exit 1
  fi
  ;;
host)
  h=${1:-}
  [ -n "$h" ] || usage
  shift
  sha=
  if [ "${1:-}" = --deployed ]; then sha=${2:?} && shift 2; fi
  [ "$#" = 0 ] || usage
  lookup "$h" "$HOSTS" >/dev/null || {
    echo "skynet-verify: no host $h (known: $HOSTS)" >&2
    exit 2
  }
  if verify_host "$h" "$sha"; then echo "verified host $h: green"; else
    echo "verified host $h: red"
    exit 1
  fi
  ;;
all)
  [ "$#" = 0 ] || usage
  sha=$(git -C "$REPO" rev-parse origin/main)
  reds=
  for tt in $TARGETS; do
    t=${tt%%=*}
    for d in $(git -C "$REPO" ls-tree -d --name-only "$sha" -- "stacks/$t/"); do
      s=${d##*/}
      verify_stack "$t" "$s" "$sha" "$(($(now) - 900))" 0 1 || reds="$reds $t/$s"
    done
  done
  for hh in $HOSTS; do
    verify_host "${hh%%=*}" || reds="$reds ${hh%%=*}"
  done
  if [ -z "$reds" ]; then echo "verified all at ${sha:0:7}: green"; else
    echo "verified all at ${sha:0:7}: red:$reds"
    exit 1
  fi
  ;;
*) usage ;;
esac
