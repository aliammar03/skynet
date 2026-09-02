#!/usr/bin/env bash
# dns-revert.sh — the L7 rollback executor for DNS writes (SKY-018 P6).
# Every DNS write (cf-dns-route.sh, and any future Technitium write) records its INVERSE command here
# BEFORE/AFTER it changes anything; this script replays that inverse to undo the write. The executor
# is a DUMB replayer (ADR 0005 §3): it re-runs a captured command, needs no agent judgement, and works
# when the thing that failed is the agent's plan. It never decides — it only reverts what was recorded.
#
# Log: append-only JSONL at $DNS_REVERT_LOG (default $XDG_STATE_HOME/skynet/dns-revert.jsonl, i.e.
# ~/.local/state/skynet — agent-owned + persisted, no root dir needed). Each line:
#   {"ts":ISO, "actuator":"cloudflare|technitium", "target":"host", "undo":["cmd","arg",...],
#    "prior":"<what was there before, for the human>", "reverted":false}
#
# TIER: T2 — the undo command is itself a T2 DNS write (scoped token). No new capability; it reverses one.
# USAGE:
#   dns-revert.sh record <actuator> <target> -- <undo-cmd...>   # a writer logs its inverse
#   dns-revert.sh list                                          # show pending (un-reverted) entries
#   dns-revert.sh undo [--target <host> | --last]               # replay the newest matching inverse
#   dns-revert.sh undo --dry-run [...]                          # print what it WOULD run, change nothing
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${DNS_REVERT_LOG:-${XDG_STATE_HOME:-${HOME}/.local/state}/skynet/dns-revert.jsonl}"
command -v jq >/dev/null || { echo "dns-revert: jq is required" >&2; exit 1; }

ensure_log() { local d; d="$(dirname "${LOG}")"; [ -d "${d}" ] || mkdir -p "${d}" 2>/dev/null || sudo -n mkdir -p "${d}"; [ -f "${LOG}" ] || : >> "${LOG}" 2>/dev/null || sudo -n touch "${LOG}"; }

cmd="${1:-list}"; shift || true
case "${cmd}" in
  record)
    actuator="${1:?actuator}"; target="${2:?target}"; shift 2
    [ "${1:-}" = "--" ] && shift
    [ "$#" -ge 1 ] || { echo "dns-revert record: need -- <undo-cmd...>" >&2; exit 1; }
    prior="${DNS_REVERT_PRIOR:-}"
    ensure_log
    # Build the undo array separately, NOT via jq --args: an undo token like `--delete` would be
    # eaten by jq's own option parser (caught by a live run — cf-dns-route's delete inverse starts
    # with --delete). Encode each token as a JSON string, then slurp into an array.
    undo_json="$(printf '%s\n' "$@" | jq -R . | jq -sc .)"
    jq -cn --arg ts "$(date -Iseconds)" --arg a "${actuator}" --arg t "${target}" \
       --arg p "${prior}" --argjson undo "${undo_json}" \
       '{ts:$ts, actuator:$a, target:$t, prior:$p, reverted:false, undo:$undo}' \
      >> "${LOG}"
    echo "dns-revert: recorded undo for ${actuator} ${target}"
    ;;
  list)
    [ -s "${LOG}" ] || { echo "no revert log yet (${LOG})"; exit 0; }
    jq -r 'select(.reverted|not) | "\(.ts)  \(.actuator)  \(.target)  ⏪ \(.undo|join(" "))  (was: \(.prior))"' "${LOG}" \
      2>/dev/null || cat "${LOG}"
    ;;
  undo)
    dry=0; target=""; last=0
    while [ "$#" -gt 0 ]; do case "$1" in
      --dry-run) dry=1;; --last) last=1;; --target) shift; target="$1";; *) echo "unknown: $1" >&2; exit 1;; esac; shift; done
    [ -s "${LOG}" ] || { echo "nothing to revert (${LOG} empty)"; exit 0; }
    # newest un-reverted entry, optionally filtered by target
    entry="$(jq -cn --arg t "${target}" '[inputs] as $x | ($x | to_entries | map(select(.value.reverted|not)
               | select($t=="" or .value.target==$t)) | last) // empty' < "${LOG}" 2>/dev/null || true)"
    [ -n "${entry}" ] || { echo "no pending revert entry${target:+ for ${target}}"; exit 0; }
    idx="$(printf '%s' "${entry}" | jq -r '.key')"
    mapfile -t undo < <(printf '%s' "${entry}" | jq -r '.value.undo[]')
    tgt="$(printf '%s' "${entry}" | jq -r '.value.target')"
    if [ "${dry}" = 1 ]; then echo "would run: ${undo[*]}  (revert ${tgt})"; exit 0; fi
    echo "reverting ${tgt}: ${undo[*]}"
    # the undo command is repo-relative (e.g. scripts/cf-dns-route.sh); run it from the repo.
    # DNS_REVERT_REPLAYING tells the writer (cf-dns-route.sh) NOT to record a counter-inverse for
    # this write — else every revert spawns a fresh pending entry and the log never settles (a live
    # run caught this: undo cf-dns-route --delete was recording a re-publish inverse in turn).
    ( cd "${REPO_DIR}" && DNS_REVERT_REPLAYING=1 "${undo[@]}" )
    # mark that entry reverted (rewrite the log with the flag flipped at $idx)
    tmp="$(mktemp)"; jq -c --argjson i "${idx}" 'to_entries[] | if .key==$i then .value + {reverted:true} else .value end' \
      < <(jq -s '.' "${LOG}") > "${tmp}" 2>/dev/null && { cat "${tmp}" > "${LOG}" 2>/dev/null || sudo -n cp "${tmp}" "${LOG}"; }
    rm -f "${tmp}"
    echo "dns-revert: reverted ${tgt}"
    ;;
  *) echo "usage: dns-revert.sh record|list|undo — see header" >&2; exit 1;;
esac
