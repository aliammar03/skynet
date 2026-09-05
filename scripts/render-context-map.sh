#!/usr/bin/env bash
# render-context-map.sh — generate docs/generated/07-context-map.md, the agent's "what can I load
# and what does it cost" index (SKY-010 P3). The twin of render-digest.sh: a fresh session reads the
# tiny always-loaded baseline, then reads THIS map to route — one row per on-demand artifact (path ·
# tier · trigger · ~tokens · summary) — and opens only the exact file it needs, instead of loading a
# whole prose catalog to choose. It's the digest doctrine extended from "what happened" to "what's
# loadable and what it costs" — the machine-readable half of the default-lean discipline
# (docs/design/memory.md).
#
# ~tokens = content-bytes / 4 (a documented heuristic), computed HERE
# at render time so the map is always fresh and self-contained — it never edits an authored file, only
# its own output under the machine-owned docs/generated/. Read-only sources, idempotent, CONTENT-STABLE
# (no per-run timestamp) so it diffs only on real change. Edit THIS renderer, never its output.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
PAGE="docs/generated/07-context-map.md"

# read one frontmatter field (strips surrounding double-quotes): fm <file> <key>
fm() { awk -v k="$2" 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{exit} f{ if($0 ~ ("^" k ":")){ sub("^" k ":[[:space:]]*",""); gsub(/^"|"$/,""); print; exit } }' "$1"; }
# ~tokens = (bytes minus any own tokens: line) / 4
toks() { local b; b=$( { grep -v '^tokens:' "$1" || true; } | wc -c); echo $(( b / 4 )); }
# summary: authored frontmatter, else first '# heading' so nothing is invisible
summ() { local s; s=$(fm "$1" summary); [ -n "$s" ] || s=$(fm "$1" title); [ -n "$s" ] || s=$(grep -m1 '^# ' "$1" 2>/dev/null | sed -E 's/^#+[[:space:]]*//'); printf '%s' "$s"; }
# tier: frontmatter tier:, else a runbook's **Tier:** prose line, else blank
tier() { local t; t=$(fm "$1" tier); [ -n "$t" ] || t=$(grep -m1 -oE '\*\*Tier:\*\*[^.]*' "$1" 2>/dev/null | sed -E 's/\*\*Tier:\*\*[[:space:]]*//'); printf '%s' "$t"; }
# escape a table cell (pipes)
esc() { printf '%s' "$1" | sed 's/|/\\|/g'; }

# file sets (deterministic order)
RUNBOOKS=$(find runbooks -type f -name '*.md' ! -name README.md -print 2>/dev/null | sort)
SPOKES=$(ls docs/design/*.md 2>/dev/null | sort)
CONV=$(ls docs/conventions/*.md 2>/dev/null | sort)
CATALOGS=$(printf '%s\n' planning/README.md compose/README.md journal/README.md runbooks/README.md templates/README.md | sort)
GENVIEWS=$(ls docs/generated/*.md 2>/dev/null | grep -v '07-context-map.md$' | sort)

base=$(( $(toks AGENTS.md) + $(toks CLAUDE.md) ))
coldboot=$(toks docs/generated/06-agent-digest.md 2>/dev/null || echo 0)

mkdir -p "$(dirname "${PAGE}")"
{
  printf -- '---\ntitle: Context Map\nauthor: skynet-ops (render-context-map.sh)\ntags: [skynet, generated, agent, context-map]\n---\n\n'
  printf '# Skynet — Context Map\n\n'
  printf -- '**Always-loaded baseline:** `AGENTS.md` + `CLAUDE.md` ≈ **%s** tok — the contract; never in this list.\n' "$base"
  printf -- '**Cold-boot read:** `docs/generated/06-agent-digest.md` ≈ %s tok.\n\n' "$coldboot"
  printf 'Everything below is **on-demand**: nothing enters context until a trigger fires. Open a *file*, not a section.\n\n'

  printf -- '## Procedures — `runbooks/` (trigger-driven)\n\n'
  printf -- '| Path | Tier | Trigger | ~tok | Summary |\n|---|---|---|--:|---|\n'
  while IFS= read -r f; do [ -n "$f" ] || continue
    printf -- '| `%s` | %s | %s | %s | %s |\n' "$f" "$(esc "$(tier "$f")")" "$(esc "$(fm "$f" trigger)")" "$(toks "$f")" "$(esc "$(summ "$f")")"
  done <<< "$RUNBOOKS"
  printf '\n'

  printf -- '## Design spokes — `docs/design/`\n\n'
  printf -- '| Path | ~tok | Summary |\n|---|--:|---|\n'
  while IFS= read -r f; do [ -n "$f" ] || continue
    printf -- '| `%s` | %s | %s |\n' "$f" "$(toks "$f")" "$(esc "$(summ "$f")")"
  done <<< "$SPOKES"
  printf '\n'

  printf -- '## Conventions — `docs/conventions/`\n\n'
  printf -- '| Path | ~tok | Summary |\n|---|--:|---|\n'
  while IFS= read -r f; do [ -n "$f" ] || continue
    printf -- '| `%s` | %s | %s |\n' "$f" "$(toks "$f")" "$(esc "$(summ "$f")")"
  done <<< "$CONV"
  printf '\n'

  printf -- '## Catalogs & templates\n\n'
  printf -- '| Path | ~tok | Summary |\n|---|--:|---|\n'
  while IFS= read -r f; do [ -n "$f" ] || continue; [ -e "$f" ] || continue
    printf -- '| `%s` | %s | %s |\n' "$f" "$(toks "$f")" "$(esc "$(summ "$f")")"
  done <<< "$CATALOGS"
  printf '\n'

  printf -- '## Generated views — `docs/generated/` (machine-owned; edit the renderer, not these)\n\n'
  printf -- '| Path | ~tok | Summary |\n|---|--:|---|\n'
  while IFS= read -r f; do [ -n "$f" ] || continue
    printf -- '| `%s` | %s | %s |\n' "$f" "$(toks "$f")" "$(esc "$(summ "$f")")"
  done <<< "$GENVIEWS"
  printf '\n'

  # Episodic memory is retrieved by TOPIC, not browsed — a pointer, not an enumeration (default-lean).
  jn=$(find journal -name '*.md' -not -name 'README.md' 2>/dev/null | wc -l | tr -d ' ')
  jt=$( { find journal -name '*.md' -not -name 'README.md' -exec cat {} + 2>/dev/null || true; } | wc -c)
  printf -- '## Episodic memory — retrieve by topic, don'"'"'t browse\n\n'
  printf -- '- `journal/` — %s raw episodes, ≈ %s tok total. Retrieve by topic: `bin/recall <topic>` (SKY-010 P4) or `grep -ri "<topic>" journal/`; recent episodes are already in `06-agent-digest.md`. **Do not load the whole store.**\n\n' "$jn" "$(( jt / 4 ))"

  # totals over the on-demand corpus (everything listed above except the episodic store)
  total=0
  for f in $RUNBOOKS $SPOKES $CONV $CATALOGS $GENVIEWS; do [ -e "$f" ] && total=$(( total + $(toks "$f") )); done
  n=$(printf '%s\n' $RUNBOOKS $SPOKES $CONV $CATALOGS $GENVIEWS | grep -c . || true)
  printf -- '---\n'
  printf -- '**On-demand corpus:** ≈ **%s** tok across %s files — but you load a *row* (≈ tens of tok) to choose, then one file.\n' "$total" "$n"
  printf -- '_A cache — regenerable from git via `render-context-map.sh`; never a source of truth._\n'
  printf '\n> [!note] Generated by `scripts/render-context-map.sh` from each loadable'"'"'s frontmatter.\n'
  printf '> Do not hand-edit. Content-stable (diffs only on real change). The **map of what you can\n'
  printf '> load and what it costs** — read a ROW, then open only the one file you need. Baseline +\n'
  printf '> this on-demand index = the default-lean discipline ([[memory]]).\n'
} > "${PAGE}"

echo "render-context-map: wrote ${PAGE}"
