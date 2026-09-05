#!/usr/bin/env bash
# documentation-drift-test.sh — guard current operational docs against known drift classes.
# TIER: T1 — reads the repository and renders only a temporary catalog; no network or credentials.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

pass=0; fail=0
ok()  { printf '  ✓ %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail + 1)); }

TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT

echo "== runbook contract and rendered catalog =="
contract_ok=1
while IFS= read -r file; do
  for key in summary tier executor rollback; do
    grep -q "^${key}:" "${file}" || { bad "${file} lacks ${key} frontmatter"; contract_ok=0; }
  done
  for section in Preconditions Steps Verify Rollback Evidence; do
    grep -q "^## ${section}$" "${file}" || { bad "${file} lacks ${section}"; contract_ok=0; }
  done
done < <(find runbooks -type f -name '*.md' ! -name README.md | sort)
[ "${contract_ok}" -eq 1 ] && ok "runbooks have required metadata and task shape"
PAGE="${TMP}/README.md" bash scripts/render-runbook-catalog.sh >/dev/null
cmp -s "${TMP}/README.md" runbooks/README.md \
  && ok "runbook catalog matches leaf frontmatter" \
  || bad "runbooks/README.md diverges from its renderer"

echo "== current-authority terminology =="
surfaces=(AGENTS.md README.md docs runbooks tofu scripts nix)
stale="$(rg -n 'planning/projects/SKY-008|svc-tofu|tofu-proxmox' "${surfaces[@]}" \
  -g '!docs/generated/**' -g '!docs/history/**' 2>/dev/null || true)"
[ -z "${stale}" ] && ok "no retired directive path or tofu identity in current authority" \
  || bad "retired operational reference remains:\n${stale}"
tokens="$(rg -n '^tokens:' docs runbooks 2>/dev/null || true)"
[ -z "${tokens}" ] && ok "no stale token frontmatter remains" || bad "stale token frontmatter remains:\n${tokens}"

echo "== saved-plan and directive placement =="
bare_apply="$(rg -n '^[[:space:]]*tofu([[:space:]].*)?[[:space:]]apply([[:space:]]|$)' runbooks 2>/dev/null || true)"
[ -z "${bare_apply}" ] && ok "runbooks have no bare production tofu apply" || bad "bare tofu apply remains:\n${bare_apply}"
misplaced="$(find planning -type f -name '*.md' ! -path 'planning/archive/*' -exec grep -l '^status: done$' {} + 2>/dev/null || true)"
[ -z "${misplaced}" ] && ok "completed directives live only in planning/archive" || bad "done directive outside archive:\n${misplaced}"

echo "== current-authority links and scripts =="
links_ok=1
while IFS= read -r file; do
  while IFS= read -r target; do
    target="${target%%#*}"
    case "${target}" in ''|http://*|https://*|mailto:*|\#*) continue ;; esac
    [ -e "$(dirname "${file}")/${target}" ] || { bad "${file} links to missing ${target}"; links_ok=0; }
  done < <(grep -oE '\]\(([^ )]+)' "${file}" | sed 's/^]('//)
done < <(printf '%s\n' AGENTS.md README.md; find docs -type f -name '*.md' ! -path 'docs/generated/*' ! -path 'docs/history/*'; find runbooks -type f -name '*.md' | sort)
[ "${links_ok}" -eq 1 ] && ok "current-authority local links resolve"

scripts_ok=1
while IFS= read -r path; do
  [ -f "${path}" ] || { bad "current authority names missing ${path}"; scripts_ok=0; }
done < <(for file in AGENTS.md README.md $(find docs runbooks -type f -name '*.md' ! -path 'docs/generated/*' ! -path 'docs/history/*'); do
  rg -o 'scripts/[A-Za-z0-9_.-]+\.sh' "${file}" || true
done | sort -u)
[ "${scripts_ok}" -eq 1 ] && ok "current-authority script references resolve"

echo
echo "documentation-drift-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
