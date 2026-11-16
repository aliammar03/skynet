#!/usr/bin/env bash
# The layout's contracts (stacks/README.md, hosts/README.md), checked from the repo's root by CI and
# by hand: every stack has compose.yaml and a README with the contract's labels in order, every host
# folder a README, and every *.sops.* file sops's metadata, so none sits in git unencrypted.
set -uo pipefail
fail=0
err() { echo "::error file=$1::$2"; fail=1; }

want='Purpose|URL|Auth mode|Data|Secrets|Upstream|Gotchas'
for d in stacks/*/*/; do
  d=${d%/}
  for f in compose.yaml README.md; do [ -f "$d/$f" ] || err "$d" "$d has no $f"; done
  [ -f "$d/README.md" ] || continue
  got=$(grep -oE '^(- \*\*(Purpose|URL|Auth mode|Data|Secrets|Upstream):\*\*|\*\*Gotchas\*\*$)' "$d/README.md" |
    sed -E 's/^- \*\*//; s/:\*\*$//; s/^\*\*Gotchas\*\*$/Gotchas/' | awk '!seen[$0]++' | paste -sd'|')
  [ "$got" = "$want" ] || err "$d/README.md" "its labels are [$got], not [$want] (stacks/README.md → The README)"
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

exit $fail
