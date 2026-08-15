#!/usr/bin/env bash
# update-clis.sh — weekly self-maintenance (A5). Runs on vm-skynet-ops as ali.
#   1. updates the agent CLIs (@openai/codex, @anthropic-ai/claude-code) to latest, and
#   2. asks EACH CLI for its provider's current --model IDs (codex→OpenAI, claude→Anthropic),
#      writing them as COMMENTED suggestions into the engine env so switching models is trivial.
#
# The suggestion block is entirely commented — it cannot change behaviour on its own; you copy a
# value into an active OPS_CODEX_MODEL / OPS_CLAUDE_MODEL line. If a CLI update breaks an engine,
# the nightly simply falls back (primary → fallback → deterministic script), so this is safe to
# run unattended.
#
# USAGE: update-clis.sh [--no-update]      (--no-update: refresh model suggestions only)
set -uo pipefail   # deliberately NOT -e: best-effort; one failing step must not abort the rest.

ENVF="${OPS_ENV_FILE:-${HOME}/.config/skynet-ops/ops.env}"
DO_UPDATE=1; [ "${1:-}" = "--no-update" ] && DO_UPDATE=0
S="# >>> model suggestions (auto-updated weekly by update-clis.sh; ALL COMMENTED — copy one into OPS_*_MODEL) <<<"
E="# <<< model suggestions <<<"
log(){ echo "[$(date -Is)] $*"; }

# 1. update the CLIs -----------------------------------------------------------
log "versions before: codex=$(codex --version 2>/dev/null || echo n/a) claude=$(claude --version 2>/dev/null || echo n/a)"
if [ "${DO_UPDATE}" = 1 ] && command -v npm >/dev/null 2>&1; then
  log "npm install -g @openai/codex@latest @anthropic-ai/claude-code@latest"
  npm install -g @openai/codex@latest @anthropic-ai/claude-code@latest 2>&1 | tail -3 || log "npm update reported issues (continuing)"
else
  log "skipping CLI update (--no-update or npm missing)"
fi
log "versions after:  codex=$(codex --version 2>/dev/null || echo n/a) claude=$(claude --version 2>/dev/null || echo n/a)"

# 2. research current model IDs (each CLI for its own provider) ----------------
# Output is sanitised to id-like tokens matching known provider families, so even a chatty
# response reduces to clean suggestions (and every emitted line is commented anyway).
sanitise(){ grep -oE '[A-Za-z0-9][A-Za-z0-9._:-]{3,}' | grep -iE 'gpt|^o[0-9]|codex|claude|opus|sonnet|haiku|fable' | sort -u | head -8; }

codex_ids=""; claude_ids=""
if command -v codex >/dev/null 2>&1; then
  codex_ids="$(timeout 150 codex exec 'List the model IDs currently selectable with the codex CLI --model flag (OpenAI). Output ONLY the ids, one per line, no prose, no bullets.' 2>/dev/null | sanitise)"
fi
if command -v claude >/dev/null 2>&1; then
  claude_ids="$(timeout 150 claude -p 'List the Anthropic model IDs currently selectable with the claude CLI --model flag. Output ONLY the ids, one per line, no prose, no bullets.' 2>/dev/null | sanitise)"
fi
log "codex model ids: $(echo ${codex_ids} | tr '\n' ' ')"
log "claude model ids: $(echo ${claude_ids} | tr '\n' ' ')"

# 3. splice a fresh commented block into the env ------------------------------
mkdir -p "$(dirname "${ENVF}")"; touch "${ENVF}"; chmod 600 "${ENVF}"
awk -v s="${S}" -v e="${E}" '$0==s{skip=1;next} $0==e{skip=0;next} skip!=1{print}' "${ENVF}" > "${ENVF}.tmp" && mv "${ENVF}.tmp" "${ENVF}"
{
  echo "${S}"
  echo "#   updated $(date -Is) · codex $(codex --version 2>/dev/null || echo n/a) · claude $(claude --version 2>/dev/null || echo n/a)"
  echo "# codex → set OPS_CODEX_MODEL to one of:"
  if [ -n "${codex_ids}" ]; then printf '#     %s\n' ${codex_ids}; else echo "#     (research unavailable this run — engine default in use)"; fi
  echo "# claude → set OPS_CLAUDE_MODEL to one of:"
  if [ -n "${claude_ids}" ]; then printf '#     %s\n' ${claude_ids}; else echo "#     (research unavailable this run — engine default in use)"; fi
  echo "${E}"
} >> "${ENVF}"
log "refreshed model suggestions in ${ENVF}"
