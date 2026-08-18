#!/usr/bin/env bash
# budget-frontmatter.sh — stamp a GENERATED `tokens:` weight into loadable docs' frontmatter, and
# report the token cost of the on-demand corpus. Part of SKY-010 (default-lean context): it turns
# "retrieve sparingly" into a NUMBER, so the audit can rank baseline offenders and the context map
# (SKY-010 P3) can show each loadable's cost for free.
#
# USAGE:
#   budget-frontmatter.sh            refresh `tokens:` across the loadable corpus + print a ranked report
#   budget-frontmatter.sh --check    NO writes; exit non-zero if any file's `tokens:` is stale/missing
#                                     or a loadable lacks a `summary:` (for the parked lint gate / CI)
#
# HEURISTIC: ~tokens = content-bytes / 4 — a documented approximation, not a real tokenizer, but good
#   enough to rank and budget. The file's own `tokens:` line is EXCLUDED from the count, so the value
#   never depends on itself → deterministic + idempotent (content-stable: re-runs diff only on real
#   change). `tokens:` is GENERATED — never hand-set (it drifts). `summary:`/`trigger:` are authored.
#
# docs/generated/ is machine-owned (its `tokens:` are the renderer's job) and is NOT written here —
# only reported. Read-only sources otherwise; engine-neutral plain bash (render-*.sh house style).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

# The loadable reference corpus this script governs (authored docs that carry frontmatter).
CORPUS_GLOBS=(docs/design/*.md docs/conventions/*.md runbooks/*.md runbooks/dr/*.md)
# Baseline references shown in the report but never written (the contract + machine-owned pages).
BASELINE_FILES=(AGENTS.md CLAUDE.md)
COLDBOOT_FILE="docs/generated/06-agent-digest.md"

CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1

has_fm() { [ "$(head -1 "$1")" = "---" ]; }
# read a single frontmatter field: fm_field <file> <key>
fm_field() { awk -v k="$2" 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{exit} f&&$0~("^"k":"){sub("^"k":[[:space:]]*","");print;exit}' "$1"; }
# content tokens = (file bytes minus its own `tokens:` line) / 4
count_tokens() { local b; b=$( { grep -v '^tokens:' "$1" || true; } | wc -c); echo $(( b / 4 )); }

stale=0; missing_summary=0; rows=""

for f in "${CORPUS_GLOBS[@]}"; do
  [ -e "$f" ] || continue
  t=$(count_tokens "$f")
  if ! has_fm "$f"; then
    rows+="$(printf '%6s  %-3s %-3s  %s' "$t" "no" "-" "$f  (NO FRONTMATTER)")"$'\n'
    [ "$CHECK" = 1 ] && { echo "check: $f has no frontmatter (needs a summary:)"; missing_summary=1; }
    continue
  fi
  sum=$(fm_field "$f" summary); trg=$(fm_field "$f" trigger); cur=$(fm_field "$f" tokens)
  [ -n "$sum" ] || { [ "$CHECK" = 1 ] && echo "check: $f lacks a summary:"; missing_summary=1; }
  hs=$([ -n "$sum" ] && echo y || echo n); ht=$([ -n "$trg" ] && echo y || echo n)
  if [ "$cur" != "$t" ]; then
    if [ "$CHECK" = 1 ]; then
      echo "check: $f tokens: is ${cur:-unset}, should be $t"; stale=1
    else
      tmp=$(mktemp)
      awk -v tok="$t" '
        NR==1&&$0=="---"{print;infm=1;next}
        infm&&$0=="---"{if(!done)print "tokens: " tok; done=1; print; infm=0; next}
        infm&&/^tokens:/{print "tokens: " tok; done=1; next}
        {print}
      ' "$f" > "$tmp" && mv "$tmp" "$f"
    fi
  fi
  rows+="$(printf '%6s  %-3s %-3s  %s' "$t" "$hs" "$ht" "$f")"$'\n'
done

printf '\n== on-demand corpus (ranked by ~tokens) ==\n'
printf '%6s  %-3s %-3s  %s\n' "~TOK" "SUM" "TRG" "FILE"
printf '%s' "$rows" | sort -rn
total=$(printf '%s' "$rows" | awk '{s+=$1} END{print s+0}')
printf '%6s  %s\n' "$total" "TOTAL on-demand corpus"

# reference weights (reported, never written)
base=0; for f in "${BASELINE_FILES[@]}"; do [ -e "$f" ] && base=$(( base + $(count_tokens "$f") )); done
printf '\n== always-loaded baseline (contract; reported, not written) ==\n'
printf '%6s  %s\n' "$base" "AGENTS.md + CLAUDE.md"
[ -e "$COLDBOOT_FILE" ] && printf '%6s  %s\n' "$(count_tokens "$COLDBOOT_FILE")" "$COLDBOOT_FILE (cold-boot read)"

if [ "$CHECK" = 1 ]; then
  if [ "$stale" = 0 ] && [ "$missing_summary" = 0 ]; then
    echo; echo "check: OK — every loadable has a summary and a fresh tokens:."; exit 0
  fi
  echo; echo "check: FAILED — run scripts/budget-frontmatter.sh to refresh tokens:; author any missing summary:."; exit 1
fi
echo; echo "budget-frontmatter: corpus refreshed."
