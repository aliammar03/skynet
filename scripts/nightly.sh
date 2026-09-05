#!/usr/bin/env bash
# nightly.sh — deterministic report-only maintenance sequence → one reviewable nightly PR.
# TIER: T1 read + generated-only PR. USAGE: nightly.sh [--prepare|--finalize] (bin/ops owns optional agent work).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

mode="${1:-run}"
case "${mode}" in run|--prepare|--finalize) ;; *) echo "usage: nightly.sh [--prepare|--finalize]" >&2; exit 2;; esac

DATE="$(date +%Y-%m-%d)"
TIME="$(date +%T)"
BRANCH="${OPS_NIGHTLY_BRANCH:-inventory/$(date +%Y-%m-%d-%H%M)}"
DEFAULT_BRANCH="${OPS_DEFAULT_BRANCH:-main}"
STATUS_FILE="${OPS_NIGHTLY_STATUS_FILE:-$(mktemp)}"
own_status_file=0
[ -n "${OPS_NIGHTLY_STATUS_FILE:-}" ] || own_status_file=1
[ -e "${STATUS_FILE}" ] || : >"${STATUS_FILE}"
cleanup() { [ "${own_status_file}" = 1 ] && rm -f "${STATUS_FILE}"; }
trap cleanup EXIT

record_failure() {
  printf '%s\n' "$1" >>"${STATUS_FILE}"
  printf 'nightly: %s failed; continuing report-only sequence\n' "$1" >&2
}

step() {
  local name="$1"; shift
  "$@" || record_failure "${name}"
}

prepare() {
  # A nightly starts only from a clean tree. This prevents a reset-to-main from discarding a
  # human's work; after this point the finalizer never resets or re-runs completed mutations.
  git diff --quiet && git diff --cached --quiet || {
    echo 'nightly: dirty worktree; refusing to prepare a generated branch' >&2
    exit 3
  }
  git fetch origin "${DEFAULT_BRANCH}" --quiet
  git checkout -B "${BRANCH}" "origin/${DEFAULT_BRANCH}"

  step collection ./scripts/collect-all.sh
  step envsync ./scripts/envsync.sh
  step render-docs ./scripts/render-docs.sh

  # Drift is evidence, not an actuator. An unavailable plan is recorded in the generated report.
  {
    if drift="$(cd "${REPO_DIR}/tofu" && eval "$(../scripts/tofu-env.sh)" && tofu plan -no-color 2>/dev/null)"; then
      printf '%s\n' "${drift}" | grep -E '^(No changes\.|Plan: |  # .* will be )' || printf 'No changes.\n'
    else
      printf 'tofu drift: plan unavailable this run (tofu env/secrets or API unreachable)\n'
      record_failure tofu-drift
    fi
  } > inventory/tofu-drift.txt 2>/dev/null || record_failure tofu-drift-report
}

write_journal() {
  local jdir jentry n diffstat failures
  jdir="journal/${DATE%%-*}"; mkdir -p "${jdir}"
  jentry="${jdir}/${DATE}-session-nightly.md"; n=2
  while [ -e "${jentry}" ]; do jentry="${jdir}/${DATE}-session-nightly-${n}.md"; n=$((n+1)); done
  diffstat="$({ git diff --stat; git diff --cached --stat; } | tail -30)"
  failures="$(sed 's/^/- /' "${STATUS_FILE}")"
  {
    printf -- '---\ndate: %s\ntime: %s\nkind: session\ntitle: nightly %s (deterministic sequence)\ntier_touched: [T1]\ngrants: []\nrefs: [runbooks/nightly.md, "%s"]\nthread_status: none\n---\n\n' \
      "${DATE}" "${TIME}" "${DATE}" "${BRANCH}"
    printf '# %s · session · nightly (deterministic sequence)\n\n' "${DATE}"
    printf 'Report-only nightly ran collection, envsync, factual rendering, and drift evidence on `%s`.\nThe optional agent stage may add a narrative and root-grant audit before this finalization.\n\n' "${BRANCH}"
    printf '## What changed before the journal entry\n\n```\n%s\n```\n\n' "${diffstat:-no staged or unstaged generated changes}"
    printf '## Actions & outcomes\n\n- Deterministic maintenance sequence completed; the journal entry was written before the final digest and context-map renders.\n\n'
    printf '## Graveyard — tried & abandoned\n\n— nothing abandoned —\n\n'
    printf '## Follow-ups / open threads\n\n'
    if [ -n "${failures}" ]; then
      printf '## Anomalies\n\n%s\n' "${failures}"
    else
      printf '— none —\n'
    fi
  } >"${jentry}"
}

finalize() {
  # The journal is intentionally before these two renders so the cold-boot digest includes this
  # run and the context map reflects the new episodic-store size.
  write_journal
  step render-digest ./scripts/render-digest.sh
  step render-context-map ./scripts/render-context-map.sh

  git add -A inventory docs/generated journal
  if git diff --cached --quiet; then
    echo 'nightly: no generated evidence to commit' >&2
    exit 4
  fi
  git commit -m "nightly ${DATE}: report-only maintenance sequence"
  git push -u origin "${BRANCH}"

  local summary pr_url
  summary="$(git diff --stat "origin/${DEFAULT_BRANCH}...${BRANCH}" -- inventory docs/generated journal compose | tail -25)"
  pr_url="$(gh pr create --base "${DEFAULT_BRANCH}" --head "${BRANCH}" \
    --title "nightly ${BRANCH#inventory/}: report-only maintenance" \
    --body "Automated report-only nightly: collection, envsync, deterministic renders, raw journal evidence, and drift report.\n\n\`\`\`\n${summary}\n\`\`\`\n\nThe merge gate may auto-merge only a generated-only, CI-green PR; otherwise this remains open for review." \
    2>&1 | tail -1)" || pr_url=""
  case "${pr_url}" in
    https://*) echo "opened ${pr_url}"; ./scripts/nightly-automerge.sh "${pr_url}" || true ;;
    *) echo "nightly: PR create failed; prepared branch preserved: ${pr_url}" >&2; exit 5 ;;
  esac
}

case "${mode}" in
  run)       prepare; finalize ;;
  --prepare) prepare ;;
  --finalize) finalize ;;
esac

echo 'nightly (deterministic) complete'
