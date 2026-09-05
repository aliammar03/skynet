#!/usr/bin/env bash
# render-digest.sh — generate docs/generated/06-agent-digest.md, the agent's cold-boot digest.
# USAGE: render-digest.sh
#   The AGENT-facing companion to the human narrative 05-state-of-the-lab.md (SKY-006 P2). A fresh
#   session reads THIS page first to orient: the settled decisions it shouldn't relitigate, the
#   threads still open, and the most recent episodes. It pulls FACTS and POINTERS — recent ADRs,
#   open SKY-### directives, recent journal episodes and the open-thread bullets those episodes
#   already carry — and it deliberately does NOT summarize journal episodes: raw episodes are
#   summarized at READ time by a human/agent, never mechanically (the SKY-006 rule).
#   docs/generated/ is MACHINE-OWNED — edit THIS renderer, never its output. Read-only sources,
#   idempotent, and CONTENT-STABLE (no per-run timestamp) so it diffs only on real change.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

PAGE="${PAGE:-docs/generated/06-agent-digest.md}"   # overridable so a test can render to a temp file
PLAN="planning"
DEC="docs/decisions"
JDIR="${JDIR:-journal}"

# read one scalar from the opening frontmatter block only; ignore inline template comments.
fm() { awk -v k="$2" 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{exit} f&&$0 ~ ("^" k ":"){sub("^" k ":[[:space:]]*","");sub(/[[:space:]]+#.*/,"");gsub(/^["]|["]$/,"");print;exit}' "$1"; }

# New episodes carry `time:`; it is the same-day ordering key. Untimed legacy episodes are kept but
# sort as unknown (`00:00:00`) rather than pretending their filename encodes chronology.
journal_files() {
  local f d t
  while IFS= read -r f; do
    d="$(fm "$f" date)"; t="$(fm "$f" time)"
    [[ "${t}" =~ ^[0-2][0-9]:[0-5][0-9](:[0-5][0-9])?$ ]] || t="00:00:00"
    printf '%sT%s\t%s\n' "${d:-0000-00-00}" "${t}" "$f"
  done < <(find "${JDIR}" -name '*.md' -not -name 'README.md' 2>/dev/null)
}

mkdir -p "$(dirname "${PAGE}")"
{
  printf -- '---\ntitle: Agent Digest\nauthor: skynet-ops (render-digest.sh)\ntags: [skynet, generated, agent, digest, cold-boot]\n---\n\n'
  printf '# Skynet — Agent Digest\n\n'
  printf 'A fresh session orients here: the settled **decisions** not to relitigate, the **open\n'
  printf 'threads** still in flight, and the most **recent episodes**. Facts and pointers only —\n'
  printf 'follow a link for the full story; distill episodes at read time, never in this file.\n\n'

  # ── Recent decisions (ADRs, newest number first) ────────────────────────────
  printf '## 🧷 Recent decisions\n\n'
  found=0
  while IFS= read -r f; do
    [ -e "$f" ] || continue
    base="$(basename "$f" .md)"
    num="$(printf '%s' "$base" | grep -oE '^[0-9]+' | sed 's/^0*//')"
    title="$(grep -m1 '^# ' "$f" | sed -E 's/^#[[:space:]]*//; s/^ADR[[:space:]]*[0-9]+[[:space:]]*[—-]?[[:space:]]*//')"
    status="$(grep -m1 -iE '^-?[[:space:]]*\*\*Status:\*\*' "$f" | sed -E 's/.*\*\*Status:\*\*[[:space:]]*//; s/[[:space:]]*$//')"
    date="$(grep -m1 -iE '^-?[[:space:]]*\*\*Date:\*\*' "$f" | sed -E 's/.*\*\*Date:\*\*[[:space:]]*//; s/[[:space:]]*$//')"
    printf -- '- **[[%s|ADR %04d]]** — %s · %s · %s\n' "$base" "${num:-0}" "${title:-?}" "${status:-?}" "${date:-?}"
    found=1
  done < <(find "${DEC}" -maxdepth 1 -name '[0-9]*-*.md' 2>/dev/null | sort -r)
  [ "$found" = 1 ] || printf -- '- _none recorded yet._\n'
  printf '\n'

  # ── Open threads: open directives, then journal follow-ups ──────────────────
  printf '## 🧵 Open threads\n\n'
  printf '**Directives in flight** (not done/abandoned):\n\n'
  # projects first (in-progress), then backlog, then ideas — most actionable at top.
  found=0
  for stage in projects backlog ideas; do
    while IFS= read -r f; do
      [ -e "$f" ] || continue
      st="$(fm "$f" status)"
      case "$st" in done|abandoned|"") continue;; esac
      id="$(fm "$f" id)"; title="$(fm "$f" title)"
      ph="$(fm "$f" current_phase)"; tp="$(fm "$f" phases)"
      phase=""; [ "$stage" = projects ] && [ -n "$tp" ] && phase=" · ${ph:-0}/${tp}"
      printf -- '- **%s** (%s · %s%s) — %s\n' "$id" "$stage" "$st" "$phase" "$title"
      found=1
    done < <(find "${PLAN}/${stage}" -maxdepth 1 -name 'SKY-*.md' 2>/dev/null | sort)
  done
  [ "$found" = 1 ] || printf -- '- _no open directives._\n'
  printf '\n'

  printf '**Explicit durable follow-ups:**\n\n'
  found=0; count=0; unknown=0
  while IFS= read -r f; do
    [ -e "$f" ] || continue
    d="$(fm "$f" date)"; k="$(fm "$f" kind)"
    case "$(fm "$f" thread_status)" in
      open) ;;
      resolved) continue ;;
      *) unknown=$((unknown+1)); continue ;;
    esac
    while IFS= read -r line; do
      case "$line" in "- <"*) continue;; esac
      printf -- '%s — _%s %s_\n' "$line" "${d:-?}" "${k:-?}"
      found=1; count=$((count+1))
      [ "$count" -ge 8 ] && break
    done < <(awk '
      /^## Follow-ups/ {f=1; next}
      /^## / {if(f && buf!="") print buf; buf=""; f=0}
      f {
        if ($0 ~ /^-[[:space:]]/)      {if(buf!="") print buf; buf=$0}
        else if ($0 ~ /^[[:space:]]*$/){if(buf!="") {print buf; buf=""}}
        else                          {sub(/^[[:space:]]+/,""); if(buf!="") buf=buf" "$0}
      }
      END {if(f && buf!="") print buf}
    ' "$f")
    [ "$count" -ge 8 ] && break
  done < <(journal_files | sort -r | cut -f2-)
  [ "$found" = 1 ] || printf -- '- _none explicitly open._\n'
  [ "$unknown" -gt 0 ] && printf -- '- _%s historical episode(s) have unclassified follow-ups; status unknown, not promoted as current work._\n' "$unknown"
  printf '\n'

  # ── Recent episodes (last 7 journal entries, newest first) ──────────────────
  printf '## 📓 Recent episodes\n\n'
  found=0
  while IFS= read -r f; do
    [ -e "$f" ] || continue
    base="$(basename "$f" .md)"
    d="$(fm "$f" date)"; k="$(fm "$f" kind)"; t="$(fm "$f" title)"
    printf -- '- **%s** · %s · [[%s|%s]]\n' "${d:-?}" "${k:-?}" "$base" "${t:-$base}"
    found=1
  done < <(journal_files | sort -r | cut -f2- | head -7)
  [ "$found" = 1 ] || printf -- '- _journal is empty — the nightly will seed it._\n'
  printf '\n---\n_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._\n'
  printf '\n> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the\n'
  printf '> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The\n'
  printf '> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.\n'
} > "${PAGE}"

echo "render-digest: wrote ${PAGE}"
