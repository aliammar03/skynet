#!/bin/sh
# The arena's lane (skynetv2.md → D18): one agent CLI on one of Ali's subscriptions, headless, one
# run at a time. The runner leaves a job in /jobs/<id>/ (job.env, prompt.txt, files/work and
# files/home, then `ready`); this copies the files into a fresh /tmp/run, runs the CLI in work/ with
# home/ as its home, and leaves its stream, last message, exit code and the files the job names to
# COLLECT beside the job, then `done`. A follow-up (RESUME: the session's id, as a person nudging the
# agent would) continues that session in the same /tmp/run. It sees no test and no answer: only its
# own job.
set -u
lane=$1

logged_in() {
  case $lane in
    codex) codex login status >/dev/null 2>&1 ;;
    claude) [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] ;;
    *) false ;;
  esac
}

run() {
  j=$1 w=/tmp/run
  RESUME=
  set -a
  . "$j/job.env"  # MODEL, EFFORT, TIMEOUT, COLLECT, RESUME and the test's names, for the agent too
  set +a
  if [ -z "$RESUME" ]; then
    rm -rf "$w" && mkdir -p "$w" && cp -R "$j/files/." "$w/" && mkdir -p "$w/work" "$w/home"
  fi
  cd "$w/work" || return
  case $lane in
    codex)  # its login and sessions stay in /codex (CODEX_HOME), as ~/.codex for the skill
      [ -e "$w/home/.codex" ] || ln -s /codex "$w/home/.codex"
      if [ -n "$RESUME" ]; then set -- exec resume "$RESUME"; else set -- exec; fi
      HOME=$w/home timeout -k 30 "$TIMEOUT" codex "$@" --json --skip-git-repo-check \
        --dangerously-bypass-approvals-and-sandbox -m "$MODEL" -c model_reasoning_effort="$EFFORT" \
        -o "$j/reply.txt" - < "$j/prompt.txt" > "$j/events.jsonl" 2> "$j/stderr.txt"
      echo $? > "$j/exit"
      t=${RESUME:-$(sed -n 's/.*"thread_id":"\([^"]*\)".*/\1/p' "$j/events.jsonl" | head -1)}
      [ -n "$t" ] && echo "$t" > "$j/session" && find /codex/sessions -name "*$t.jsonl" -exec cp {} "$j/session.jsonl" \;
      ;;
    claude)  # its login is the token in its environment; a fresh home each run (kept for a follow-up)
      HOME=$w/home timeout -k 30 "$TIMEOUT" claude -p ${RESUME:+--resume "$RESUME"} --output-format stream-json \
        --verbose --dangerously-skip-permissions --model "$MODEL" --effort "$EFFORT" \
        < "$j/prompt.txt" > "$j/events.jsonl" 2> "$j/stderr.txt"
      echo $? > "$j/exit"
      sed -n 's/.*"session_id":"\([^"]*\)".*/\1/p' "$j/events.jsonl" | tail -1 > "$j/session"
      ;;
  esac
  for f in $COLLECT; do
    [ -f "$w/$f" ] && mkdir -p "$j/collected/$(dirname "$f")" && cp "$w/$f" "$j/collected/$f"
  done
}

while :; do
  if ! logged_in; then
    echo "not logged in" > /jobs/.status
    sleep 30
    continue
  fi
  echo ready > /jobs/.status
  for j in /jobs/*/; do
    j=${j%/}
    [ -f "$j/ready" ] && [ ! -e "$j/taken" ] || continue
    : > "$j/taken"
    echo "$(date -Is) ${j##*/} $(sed -n 's/^MODEL=//p' "$j/job.env") start"
    (run "$j")
    : > "$j/done"
    echo "$(date -Is) ${j##*/} exit $(cat "$j/exit" 2>/dev/null)"
  done
  sleep 2
done
