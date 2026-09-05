#!/usr/bin/env bash
# compose-rollback-test.sh — the L7 Compose rollback executor + gate (SKY-018 P6) in the FAILURE case.
#   The deterministic gate (deploy-gate.sh) must, on an unhealthy probe, fire the executor
#   (gitops-rollback.sh); on a healthy probe it must NOT. The executor must prepare a local `git
#   revert` but never direct-push an authored revert; human review/merge is required. The rollback
#   DECISION is the gate's, never the agent's — proven by injecting the probe result and asserting the
#   executor ran. No Arcane, no docker, no network: externals stubbed.
# TIER: T1 — stubbed git + injected probe; changes nothing real.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  \342\234\223 %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \342\234\227 %s\n' "$1" >&2; fail=$((fail+1)); }

TMP="$(mktemp -d)"; trap 'rm -f "${TMP}"/* 2>/dev/null; rmdir "${TMP}" 2>/dev/null' EXIT
GATE="scripts/deploy-gate.sh"

# --- 1. FAILURE case: an unhealthy probe must fire the executor -----------------------------------
# Stub executor: records that it ran and with what args (proves the gate DECIDED to roll back).
cat > "${TMP}/rollback-stub.sh" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" > "${TMP}/rollback.args"
EOF
chmod +x "${TMP}/rollback-stub.sh"

DEPLOY_GATE_TIMEOUT=0 DEPLOY_GATE_PROBE='echo "container x=unhealthy"; false' \
  GITOPS_ROLLBACK="${TMP}/rollback-stub.sh" \
  "${GATE}" karakeep deadc0ffee >/dev/null 2>&1
rc=$?
[ "${rc}" -ne 0 ] && ok "unhealthy probe → gate exits non-zero" || bad "gate returned 0 on an unhealthy deploy"
if [ -f "${TMP}/rollback.args" ] && grep -q '^karakeep deadc0ffee' "${TMP}/rollback.args"; then
  ok "unhealthy probe → executor fired with (service, deploy-commit)"
else
  bad "executor did not fire (or wrong args): $(cat "${TMP}/rollback.args" 2>/dev/null || echo MISSING)"
fi

# --- 2. HEALTHY case: a passing probe must NOT roll back ------------------------------------------
rm -f "${TMP}/rollback.args"
DEPLOY_GATE_TIMEOUT=0 DEPLOY_GATE_PROBE='true' \
  GITOPS_ROLLBACK="${TMP}/rollback-stub.sh" \
  "${GATE}" karakeep deadc0ffee >/dev/null 2>&1
rc=$?
[ "${rc}" -eq 0 ] && ok "healthy probe → gate exits 0 (deploy kept)" || bad "gate failed a healthy deploy"
[ ! -f "${TMP}/rollback.args" ] && ok "healthy probe → executor NOT fired" || bad "executor fired on a healthy deploy"

# --- 3. The executor itself: it must `git revert` locally and never direct-push -------------------
# Stub git on PATH: log every call; a non-merge commit has no ^2 (rev-parse ^2 → exit 1).
cat > "${TMP}/git" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "${TMP}/git.log"
if [ "\$1" = branch ] && [ "\$2" = --show-current ]; then printf 'main\n'; exit 0; fi
if [ "\$1" = show-ref ]; then exit 1; fi
if [ "\$1" = rev-parse ]; then case "\$*" in *'^2'*) exit 1;; *) exit 0;; esac; fi
exit 0
EOF
chmod +x "${TMP}/git"
: > "${TMP}/git.log"
GITOPS_ROLLBACK_NO_RECONCILE=1 PATH="${TMP}:${PATH}" \
  scripts/gitops-rollback.sh karakeep deadc0ffee >/dev/null 2>&1
rc=$?
[ "${rc}" = 3 ] && ok "default executor reports failure without mutating git" || bad "default executor did not report-only (rc=${rc})"
! grep -q 'revert ' "${TMP}/git.log" && ok "report-only path does not create a revert" || bad "report-only path mutated git"
! grep -q '^push' "${TMP}/git.log" && ok "report-only path does not push" || bad "report-only path pushed"

# Explicit preparation uses an isolated worktree and review branch, with no direct push.
: > "${TMP}/git.log"
GITOPS_ROLLBACK_NO_RECONCILE=1 PATH="${TMP}:${PATH}" \
  scripts/gitops-rollback.sh karakeep deadc0ffee --prepare >/dev/null 2>&1
grep -q 'worktree add -b rollback/karakeep-deadc0ffee ' "${TMP}/git.log" \
  && ok "--prepare creates an isolated review branch" || bad "--prepare did not create an isolated worktree"
grep -q 'revert --no-edit deadc0ffee' "${TMP}/git.log" \
  && ok "--prepare runs git revert in the worktree" || bad "--prepare did not git-revert the commit"
! grep -q '^push' "${TMP}/git.log" && ok "--prepare never direct-pushes authored revert" || bad "--prepare pushed an authored revert"

# An explicit push request is rejected rather than providing an escape hatch around the merge gate.
if GITOPS_ROLLBACK_NO_RECONCILE=1 PATH="${TMP}:${PATH}" \
  scripts/gitops-rollback.sh karakeep deadc0ffee --push >/dev/null 2>&1; then
  bad "executor accepted an explicit direct-push request"
else
  ok "explicit direct-push request is rejected"
fi

echo
echo "compose-rollback-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
