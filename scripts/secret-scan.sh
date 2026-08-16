#!/usr/bin/env bash
# secret-scan.sh — pre-commit guard for AGENTS.md §6: "never plaintext secrets in commits."
# Wired as the repo's pre-commit hook (see .githooks/pre-commit; enable with
#   git config core.hooksPath .githooks   — bootstrap-workstation.sh does this for you).
#
# It scans the STAGED tree only, and enforces the two sanctioned layers from compose/README.md:
#   *.env.git  — non-secret config, committed plaintext (ALLOWED)
#   *.env.sops — secrets, sops+age encrypted            (ALLOWED)
# Anything else that looks like a secret — a plaintext .env/project.env, a *.key/*.pem, a
# PRIVATE KEY block, or a high-entropy TOKEN/SECRET/PASSWORD assignment — is blocked.
#
# Escape hatch (use only when you are certain the match is a false positive):
#   git commit --no-verify
set -euo pipefail

# Staged additions/copies/modifications, NUL-safe (handles spaces/newlines in paths).
mapfile -d '' -t staged < <(git diff --cached --name-only --diff-filter=ACM -z)
[ "${#staged[@]}" -gt 0 ] || exit 0

fail=0
note() { printf '  \342\234\227 %s\n' "$1" >&2; fail=1; }

# 1) Forbidden secret-bearing filenames — the plaintext layers that must never be committed.
for f in "${staged[@]}"; do
  case "${f}" in
    *.env.sops|*.env.git) : ;;                                  # sanctioned layers — always OK
    *.key|*.pem|*id_ed25519)
      note "${f}: secret-bearing filename must never be committed" ;;
    *.env)
      note "${f}: plaintext env must never be committed (use .env.git + .env.sops)" ;;
  esac
done

# 2) Content scan — private-key blocks + hardcoded secret assignments — over the staged blob,
#    skipping the sanctioned/encrypted/public layers where such patterns are expected or inert.
for f in "${staged[@]}"; do
  case "${f}" in *.env.sops|*.env.git|*.pub) continue ;; esac
  blob="$(git show ":${f}" 2>/dev/null)" || continue
  if grep -qE 'BEGIN ([A-Z0-9]+ )?PRIVATE KEY' <<<"${blob}"; then
    note "${f}: contains a PRIVATE KEY block"
  fi
  if grep -qEi '(API_?KEY|SECRET|TOKEN|PASSWORD|PASSWD)[[:space:]]*[:=][[:space:]]*"?[A-Za-z0-9/_+=.-]{20,}' <<<"${blob}"; then
    note "${f}: looks like a hardcoded secret assignment"
  fi
done

if [ "${fail}" -ne 0 ]; then
  {
    echo ""
    echo "pre-commit BLOCKED: plaintext secrets must be sops-encrypted (.env.sops) or kept 0600 out of the tree."
    echo "If you are certain a match is a false positive: git commit --no-verify"
  } >&2
  exit 1
fi
