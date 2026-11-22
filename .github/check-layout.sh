#!/usr/bin/env bash
# The layout's contracts (stacks/README.md, hosts/README.md), checked from the repo's root by CI and
# by hand:
# - every stack has compose.yaml and a README with the contract's labels in order;
# - every compose.yaml keeps the contract: a container_name and an image pinned by digest for each
#   service, no named volumes, no mount of the stack's folder, and a job in a stack of jobs alone
#   with reconciliation off;
# - no stack's name begins with another's on the same host;
# - every host folder has a README;
# - every *.sops.* file has sops's metadata, so none sits in git unencrypted;
# - every repo path a file names exists, or is planned (named in docs/plans/).
set -uo pipefail
fail=0
err() { echo "::error file=$1::$2"; fail=1; }

want='Purpose|URL|Auth mode|Data|Secrets|Upstream|Gotchas'
for d in stacks/*/*/; do
  d=${d%/}
  for f in compose.yaml README.md; do [ -f "$d/$f" ] || err "$d" "$d has no $f"; done
  if [ -f "$d/README.md" ]; then
    got=$(grep -oE '^(- \*\*(Purpose|URL|Auth mode|Data|Secrets|Upstream):\*\*|\*\*Gotchas\*\*$)' "$d/README.md" |
      sed -E 's/^- \*\*//; s/:\*\*$//; s/^\*\*Gotchas\*\*$/Gotchas/' | awk '!seen[$0]++' | paste -sd'|')
    [ "$got" = "$want" ] || err "$d/README.md" "its labels are [$got], not [$want] (stacks/README.md → The README)"
  fi

  [ -f "$d/compose.yaml" ] || continue
  # Anchors and merge keys resolved, so a label or an image set through one counts.
  c=$(yq -o=json 'explode(.)' "$d/compose.yaml" 2>/dev/null) || { err "$d/compose.yaml" "$d/compose.yaml doesn't parse"; continue; }
  while IFS= read -r msg; do
    err "$d/compose.yaml" "$d: $msg (stacks/README.md → The folder)"
  done < <(jq -r '
    def job: (.labels // {}) | if type == "array" then any(.[]; test("^cd\\.doco\\.job\\.enabled=\"?true"))
      else ((."cd.doco.job.enabled" // "") | tostring) == "true" end;
    (.services // {} | to_entries) as $s
    | ($s[] | .key as $n | .value
        | (if .container_name then empty else "service \($n) has no container_name" end),
          (if .build or ((.image // "") | test("@sha256:[0-9a-f]{64}$")) then empty
            else "service \($n): its image isn'"'"'t pinned as tag@sha256:…" end),
          ((.volumes // [])[] | (if type == "string" then split(":")[0] else (.source // "") end)
            | select(. == "." or . == "./") | "service \($n) mounts the stack'"'"'s folder itself")),
      ((.volumes // {}) | keys[] | "named volume \(.): data is a bind mount under /opt/appdata"),
      (if any($s[]; .value | job) and any($s[]; .value | job | not)
        then "a job sits beside long-running services: a job is a stack of its own" else empty end)
  ' <<<"$c")
  if jq -e 'any(.services[]?; (.labels // {}) | if type == "array" then any(.[]; test("^cd\\.doco\\.job\\.enabled=\"?true"))
      else ((."cd.doco.job.enabled" // "") | tostring) == "true" end)' <<<"$c" >/dev/null; then
    [ "$(yq '.reconciliation == false or .reconciliation.enabled == false' "$d/.doco-cd.yml" 2>/dev/null)" = true ] ||
      err "$d" "$d holds a job, so its .doco-cd.yml turns reconciliation off (stacks/README.md → The folder)"
  fi
done

# doco-cd gives a container's event to the first stack whose name begins the container's own,
# followed by -, _ or . (matchCandidateStackName in its source), so `x-job`'s events would go to `x`.
for t in stacks/*/; do
  for a in "$t"*/; do
    a=$(basename "$a")
    for b in "$t"*/; do
      b=$(basename "$b")
      case "$b" in
        "$a"-* | "$a"_* | "$a".*)
          err "$t$b" "stack $b's name begins with stack $a's: doco-cd would give $b's container events to $a (stacks/README.md → The folder)" ;;
      esac
    done
  done
done

# Every routed app has a Gatus row, so verify sees it answer through its door
# (docs/plans/autonomy.md → Verify and roll back): a row or suite step whose URL's host is one of the
# site's hosts or one of its upstreams. A site with none says why in a line `# No Gatus row: <why>`.
rows=$(for g in stacks/admin/gatus/config/*.yaml; do
  yq -o=json 'explode(.)' "$g" | jq -r '(.endpoints // [])[], ((.suites // [])[].endpoints[]) | .url'
done | sed -E 's#^[a-z]+://##; s#[:/].*$##' | sort -u)
for f in stacks/*/caddy-*/conf/sites/*.conf; do
  grep -q '^# No Gatus row: ' "$f" && continue
  hosts=$(sed -nE 's#^@[^ ]+ host (.+)$#\1#p; s#^\s*reverse_proxy\s+(https?://)?([^:/ {]+).*#\2#p' "$f" | tr ' ' '\n')
  grep -qxFf <(printf '%s\n' "$hosts") <<<"$rows" ||
    err "$f" "$f routes $(sed -nE 's#^@[^ ]+ host (.+)$#\1#p' "$f" | head -n1), which has no Gatus row: add one, or say why in '# No Gatus row: <why>' (stacks/README.md → Routing)"
done

for d in hosts/*/; do
  [ -f "${d}README.md" ] || err "${d%/}" "${d%/} has no README.md (hosts/README.md)"
done

while IFS= read -r f; do
  case "$f" in
    *.env) grep -q '^sops_mac=ENC\[' "$f" && grep -q '^sops_version=' "$f" ;;
    *.yaml | *.yml) [ "$(yq '.sops.mac // "" | test("^ENC\\[")' "$f" 2>/dev/null)" = true ] ;;
    *.conf) grep -q '^\[sops\]' "$f" && grep -qE '^mac *= *ENC\[' "$f" ;;
    *) false ;;
  esac || err "$f" "$f has no sops metadata: encrypt it (sops encrypt …) before it reaches git"
done < <(git ls-files '*.sops.*' ':!.sops.yaml')

# A path under one of the repo's folders, wherever a file names it: a README, a runbook, a comment.
# lychee sees only Markdown links, and most references here are plain or backticked paths. A path
# with a placeholder (`hosts/<name>/`, `stacks/*/`), one inside a longer path (`/etc/…/modules/x`)
# and a variable's (`$d/hosts/…`) aren't ours to check. A path that doesn't exist yet passes while
# a plan names it.
re='(?<![\w/.-])(?:(?:\.github|dns|hosts|modules|packages|runbooks|stacks|docs/decisions|docs/plans)/[\w./-]*+|docs/[a-z]+\.md)(?![<*{$\w])'
while IFS=: read -r f l p; do
  while [[ $p == *. || $p == */ ]]; do p=${p%?}; done
  [ -e "$p" ] || grep -rqF -- "$p" docs/plans 2>/dev/null ||
    err "$f" "$f:$l names $p, which doesn't exist"
done < <(git grep -InoP "$re" -- . ':!*.sops.*' ':!flake.lock' ':!docs/plans')

exit $fail
