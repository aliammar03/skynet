#!/usr/bin/env bash
# render-runbook-catalog.sh — render runbooks/README.md from leaf frontmatter.
# The README is a routing menu, not a second handwritten source of truth. Edit leaf metadata or this
# renderer; never hand-edit the rendered catalog.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
PAGE="${PAGE:-runbooks/README.md}"

# fm <file> <key>: one small YAML frontmatter scalar, with surrounding double quotes removed.
fm() { awk -v k="$2" 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{exit} f{if($0 ~ ("^" k ":")){sub("^" k ":[[:space:]]*","");gsub(/^"|"$/," ");sub(/^ /,"");sub(/ $/,"");print;exit}}' "$1"; }
esc() { printf '%s' "$1" | sed 's/|/\\|/g'; }
tier() { local t; t="$(fm "$1" tier)"; [ -n "${t}" ] || t="$(grep -m1 -oE '\*\*Tier:\*\*[^.]*' "$1" 2>/dev/null | sed -E 's/\*\*Tier:\*\*[[:space:]]*//')"; printf '%s' "${t}"; }

RUNBOOKS="$(find runbooks -type f -name '*.md' ! -name README.md -print | sort)"
{
  printf -- '---\nsummary: "Catalog of task-shaped, engine-neutral operational procedures. Rendered from runbook frontmatter."\n---\n\n'
  printf '# runbooks — procedures any agent can execute\n\n'
  printf 'A runbook is engine-neutral markdown plus plain bash. Read the leaf whose trigger matches the task; do not load unrelated procedures.\n\n'
  printf '## Catalog\n\n'
  printf '| Runbook | Tier | Trigger | Summary |\n|---|---|---|---|\n'
  while IFS= read -r file; do
    [ -n "${file}" ] || continue
    printf '| [`%s`](%s) | %s | %s | %s |\n' \
      "${file#runbooks/}" "${file#runbooks/}" "$(esc "$(tier "${file}")")" \
      "$(esc "$(fm "${file}" trigger)")" "$(esc "$(fm "${file}" summary)")"
  done <<<"${RUNBOOKS}"
  printf '\n## Runbook contract\n\n'
  printf -- '- Use compact frontmatter: `summary`, `trigger` where natural, `tier`, `executor`, and `rollback`.\n'
  printf -- '- Structure every leaf as **Preconditions → Steps → Verify → Rollback → Evidence**.\n'
  printf -- '- Keep procedures current and task-shaped; doctrine belongs in its authoritative design/convention document, history in `journal/`.\n'
  printf '\n_A cache — regenerate with `scripts/render-runbook-catalog.sh`; never hand-edit._\n'
} >"${PAGE}"

echo "render-runbook-catalog: wrote ${PAGE}"
