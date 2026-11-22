# skynet-merge: whether the window may merge a PR now, gate by gate (docs/plans/autonomy.md →
# Merges). It reads GitHub, the PR's own files and the lab; it prints each gate and exits 0 only when
# all pass. A dry run until step 6: it never takes the undo point or merges, only says it would.
# modules/window.nix sets REPO (the agent's clone), GH_ENV (the bot's token, for gh alone), STATE
# (the window's state: rolled-back PRs), LOGS (VictoriaLogs, for Unraid's undo copy) and AGE (how
# old a Renovate PR's newest commit must be, in seconds).

usage() {
  cat >&2 <<'EOF'
usage: skynet-merge <pr> [--asked]
       skynet-merge --tier <pr>
  <pr>:   every gate for the PR now, and what the window would do. --asked: Ali asked for it in
          chat (his message is linked in the PR), so the window and the release's age don't apply.
  --tier: the PR's tier and stack only ("A dmz/komga", "B", "C"), from its files and labels.
EOF
  exit 2
}

github=aliammar03/skynet
# gh with the bot's token, which nothing else here sees
ghx() { (
  set -a
  # shellcheck disable=SC1090 # rendered by sops-nix
  [ -z "${GH_ENV:-}" ] || . "$GH_ENV"
  gh "$@"
); }
now() { date +%s; }
pass() { printf '  ok    %s\n' "$*"; }
no() {
  printf '  no    %s\n' "$*"
  blocked=$((blocked + 1))
}

# The tier a PR's files give it, the floor; a label may only raise it:
# - A: every file in one stack's folder, `stacks/<target>/<stack>/` (Renovate's stack PRs, a fix);
# - B: a host's, any of flake.nix, flake.lock, modules/, packages/, dns/ and the NixOS hosts' folders;
# - C: anything else (more than one stack, a machine that isn't NixOS, a code owner's file, docs).
# A label `tier:B` or `tier:C` raises it; nothing lowers it.
tier_of() { # <pr json> → "A <target>/<stack>" | "B" | "C"
  jq -r '
    [.files[].path] as $f
    | ([$f[] | capture("^stacks/(?<t>[a-z]+)/(?<s>[a-z0-9-]+)/") | "\(.t)/\(.s)"] | unique) as $stacks
    | (if ($f | length) > 0 and ($stacks | length) == 1 and all($f[]; startswith("stacks/\($stacks[0])/")) then "A"
       elif all($f[]; test("^(flake\\.(nix|lock)$|modules/|packages/|dns/|hosts/(ops|docker-admin|docker-dmz|technitium-core|technitium-network)/)"))
         and (any($f[]; test("^(\\.github/|modules/window\\.nix$|packages/skynet-(merge|verify|window)/)")) | not) then "B"
       else "C" end) as $floor
    | ([.labels[].name | select(test("^tier:[ABC]$")) | ltrimstr("tier:")] + [$floor] | max) as $tier
    | if $tier == "A" then "A \($stacks[0])" else $tier end' <<<"$1"
}

[ "$#" -ge 1 ] || usage
if [ "$1" = --tier ]; then
  [[ ${2:-} =~ ^[0-9]+$ ]] || usage
  tier_of "$(ghx pr view "$2" --repo "$github" --json files,labels)"
  exit 0
fi
[[ $1 =~ ^[0-9]+$ ]] || usage
pr=$1 asked=
[ "${2:-}" != --asked ] || asked=1
[ "$#" -le 2 ] || usage

fields=number,title,body,state,isDraft,baseRefName,headRefOid,author,labels,files,commits,mergeable,statusCheckRollup,comments,url
j=$(ghx pr view "$pr" --repo "$github" --json "$fields") || {
  echo "skynet-merge: can't read #$pr" >&2
  exit 2
}
# GitHub works out mergeability on first asking: ask again for an answer.
if [ "$(jq -r .mergeable <<<"$j")" = UNKNOWN ]; then
  sleep 5
  j=$(ghx pr view "$pr" --repo "$github" --json "$fields")
fi
sha=$(jq -r .headRefOid <<<"$j")
author=$(jq -r .author.login <<<"$j")
blocked=0
echo "== #$pr ${sha:0:7} $(jq -r .title <<<"$j")"

# The PR: open, ready, onto main, with no conflict
if jq -e '.state == "OPEN" and (.isDraft | not) and .baseRefName == "main"' <<<"$j" >/dev/null; then
  pass "open, ready, onto main"
else
  no "not an open, ready PR onto main ($(jq -r '"\(.state), draft \(.isDraft), onto \(.baseRefName)"' <<<"$j"))"
fi
m=$(jq -r .mergeable <<<"$j")
if [ "$m" = MERGEABLE ]; then pass "no conflict with main"; else no "mergeable: $m"; fi

# The tier: only A merges in the window until hosts prove themselves under a timed rollback (step 7)
read -r tier stack <<<"$(tier_of "$j")"
case "$tier" in
A) pass "tier A: $stack" ;;
B) no "tier B, a host's: merges once a host change proves itself under a timed rollback (step 7)" ;;
*) no "tier C: Ali's" ;;
esac
if jq -e 'any(.labels[]; .name == "steps")' <<<"$j" >/dev/null; then
  no "labelled steps: the agent takes it after the window's script, by hand"
fi

# A job's stack: its verify runs the job, which needs doco-cd's trigger (step 6)
if [ "$tier" = A ]; then
  t=${stack%%/*} s=${stack#*/}
  if git -C "$REPO" show "$sha:stacks/$t/$s/compose.yaml" 2>/dev/null | yq -o=json 'explode(.)' 2>/dev/null |
    jq -e '[.services[] | (.labels // {}) | if type == "array" then any(.[]; test("^cd\\.doco\\.job\\.enabled=\"?true"))
      else ((."cd.doco.job.enabled" // "") | tostring) == "true" end] | all' >/dev/null; then
    no "a stack of jobs: verify can't run its job yet (step 6)"
  fi
fi

# CI: nix and build passed on this commit, and nothing failed or is still running
ci=$(jq -r '[.statusCheckRollup[] | {n: (.name // .context), c: ((.conclusion // .state // .status) | ascii_downcase)}] as $r
  | ([("nix", "build") as $want | select(any($r[]; .n == $want and .c == "success") | not) | "\($want) hasn'"'"'t passed"]
     + [$r[] | select(.c != "success" and .c != "neutral" and .c != "skipped") | "\(.n) \(.c)"]) | unique | join(", ")' <<<"$j")
if [ -z "$ci" ]; then pass "CI: nix and build passed, nothing else failing"; else no "CI: $ci"; fi

# The review: the evening run's, on this very commit, saying merge
verdict=$(jq -r --arg sha "$sha" '[.comments[] | select(.author.login == "aliammar-skynet")
  | .body | capture("<!-- skynet-review (?<sha>[0-9a-f]{40}) (?<v>[a-z]+) -->") | select(.sha == $sha) | .v] | last // "none"' <<<"$j")
case "$verdict" in
merge) pass "review: merge, on ${sha:0:7}" ;;
none) no "review: none on ${sha:0:7} yet (the evening run's)" ;;
*) no "review: $verdict, on ${sha:0:7}" ;;
esac

# Renovate's: its newest commit is old enough (most registries give no release time, renovate.json)
if [ "$author" = app/renovate ] && [ -z "$asked" ]; then
  at=$(jq -r '.commits[-1].committedDate' <<<"$j")
  age=$(($(now) - $(date -d "$at" +%s)))
  if [ "$age" -ge "$AGE" ]; then
    pass "age: its newest commit is $((age / 86400)) days old"
  else
    no "age: its newest commit is $((age / 3600)) hours old; it merges from $(date -d "@$(($(date -d "$at" +%s) + AGE))" '+%a %d %H:%M')"
  fi
fi

# Not this commit again after a rollback: the next review names what changed
if grep -qxF "$pr $sha" "$STATE/rolled-back" 2>/dev/null; then
  no "rolled back before at ${sha:0:7}: a second try needs a new commit and a review naming what changed"
fi

# The window: 05:00–06:00, while nobody uses the apps; what Ali asks for goes out at once
h=$(date +%H)
if [ -n "$asked" ]; then
  if jq -e '.body | test("https://discord\\.com/channels/[0-9]+/[0-9]+/[0-9]+")' <<<"$j" >/dev/null; then
    pass "asked for in chat (his message is linked): out now"
  else
    no "asked for in chat, but the PR doesn't link his message"
  fi
elif [ "$h" = 05 ]; then
  pass "in the window"
else
  no "outside the window (05:00–06:00)"
fi

# Only now the lab, and only for a stack PR that passed the rest: the stack is well before it
# changes, and a library writer has tonight's copy of Storage
if [ "$tier" = A ] && [ "$blocked" = 0 ]; then
  if out=$(skynet-verify stack "$stack" --now 2>&1); then
    pass "the stack is well now ($stack)"
  else
    no "the stack isn't well now: $(grep FAIL <<<"$out" | head -n 3 | sed 's/^ *FAIL *//' | paste -sd';')"
  fi
  case "$s" in
  clu | uchiyomi | comics-agent)
    copy=$(curl -fsS --max-time 30 "$LOGS/select/logsql/query" --data-urlencode \
      "query=_time:1d source:=unraid app_name:=skynet-undo \"to undo-Storage/$(date +%F)\" | stats count() as n" | jq -r '.n // "0"') || copy=0
    if [ "$copy" -gt 0 ]; then pass "library: tonight's copy of Storage is done"; else no "library: no copy of Storage tonight (hosts/unraid/README.md → Undo copies)"; fi
    ;;
  esac
fi

if [ "$blocked" = 0 ]; then
  host=$([ "${stack%%/*}" = admin ] && echo docker-admin || echo docker-dmz)
  echo "would merge #$pr ${sha:0:7} ($stack): btrbk's snapshot of /opt/appdata on $host as its undo point, the merge of ${sha:0:7} alone, then skynet-verify stack $stack --ref <the merge> (dry run: none of it done)"
  exit 0
fi
echo "not merging #$pr: $blocked gates"
exit 1
