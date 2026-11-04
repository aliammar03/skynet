#!/bin/sh
# The arena's lane (skynetv2.md → D18): one agent CLI on one of Ali's subscriptions, headless, one
# run at a time. The runner leaves a job in /jobs/<id>/ (job.env, prompt.txt, files/work and
# files/home, then `ready`); this copies the files into a fresh /tmp/run, runs the CLI in work/ with
# home/ as its home, and leaves its stream, last message, exit code and the files the job names to
# COLLECT beside the job, then `done`. It sees no suite and no answer: only its own job.
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
  set -a
  . "$j/job.env"  # MODEL, EFFORT, TIMEOUT, COLLECT and the suite's names, for the agent too
  set +a
  rm -rf "$w" && mkdir -p "$w" && cp -R "$j/files/." "$w/" && mkdir -p "$w/work" "$w/home"
  cd "$w/work" || return
  case $lane in
    codex)  # its login and sessions stay in /codex (CODEX_HOME), as ~/.codex for the skill
      ln -s /codex "$w/home/.codex"
      HOME=$w/home timeout -k 30 "$TIMEOUT" codex exec --json --skip-git-repo-check \
        --dangerously-bypass-approvals-and-sandbox -m "$MODEL" -c model_reasoning_effort="$EFFORT" \
        -o "$j/reply.txt" - < "$j/prompt.txt" > "$j/events.jsonl" 2> "$j/stderr.txt"
      echo $? > "$j/exit"
      t=$(sed -n 's/.*"thread_id":"\([^"]*\)".*/\1/p' "$j/events.jsonl" | head -1)
      [ -n "$t" ] && find /codex/sessions -name "*$t.jsonl" -exec cp {} "$j/session.jsonl" \;
      ;;
    claude)  # its login is the token in its environment; a fresh home each run
      HOME=$w/home timeout -k 30 "$TIMEOUT" claude -p --output-format stream-json --verbose \
        --dangerously-skip-permissions --model "$MODEL" --effort "$EFFORT" \
        < "$j/prompt.txt" > "$j/events.jsonl" 2> "$j/stderr.txt"
      echo $? > "$j/exit"
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
