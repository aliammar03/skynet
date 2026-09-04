#!/usr/bin/env bash
# check-invariants.sh — assert the machine-checkable hard laws (invariants.json) against observed
#   inventory + the tracked tree; exit non-zero on any violation. → the deterministic gate (SKY-011)
# TIER: T1 — reads repo files + runs read-only greps. No network, no secrets, no writes.
# USAGE: check-invariants.sh   (run from anywhere; reads invariants.json + inventory/proxmox-*.json)
#   The whole point (ADR 0003): a NON-LLM process consumes invariants.json, so the hard laws are
#   enforced by this script, not by the agent remembering. Wired into .githooks/ + CI.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

INV="invariants.json"
[ -r "${INV}" ] || { echo "check-invariants: ${INV} not found at repo root" >&2; exit 2; }
command -v jq >/dev/null || { echo "check-invariants: jq is required" >&2; exit 2; }

fail=0
violation() { printf '  \342\234\227 %s\n' "$1" >&2; fail=1; }
ok()        { printf '  \342\234\223 %s\n' "$1"; }
# canonical node name for an inventory file (the node-typed resource; falls back to top-level .node)
node_of() { jq -r '(.nodes[]? | select(.type=="node") | .node) // .node' "$1"; }

# --- 1. Excluded guests never appear as a pool member -------------------------------------------
echo "== excluded guests are never pooled =="
before=${fail}
mapfile -t excluded < <(jq -r '.excluded_guests.guests[].vmid' "${INV}")
for invf in inventory/proxmox-*.json; do
  [ -e "${invf}" ] || continue
  node="$(node_of "${invf}")"
  # A pool with members:null means membership was unreadable at collect time — we cannot verify the
  # exclusion, so fail loudly rather than pass blind (fix Pool.Audit on the pool path, then recollect).
  if jq -e '[.pools[]? | select(.members == null)] | length > 0' "${invf}" >/dev/null; then
    violation "${node} (${invf}): a pool has members:null (unreadable) — cannot verify exclusions"
  fi
  for vmid in "${excluded[@]}"; do
    if jq -e --argjson v "${vmid}" '[.pools[]?.members[]? | select(.vmid == $v)] | length > 0' "${invf}" >/dev/null; then
      pools="$(jq -r --argjson v "${vmid}" '[.pools[]? | select(any(.members[]?; .vmid == $v)) | .poolid] | join(", ")' "${invf}")"
      violation "${node}: excluded guest ${vmid} is a member of pool(s) [${pools}] — it must NEVER join a pool"
    fi
  done
done
[ "${fail}" -eq "${before}" ] && ok "no excluded VMID (${excluded[*]}) appears in any pool"

# --- 2. The ops-managed pool set: observed == declared -----------------------------------------
echo "== ops-managed pool set matches the declared blast-radius dial =="
before=${fail}
declared="$(jq -r '.ops_managed_pools.pools[] | "\(.node)\t\(.pool)"' "${INV}" | sort)"
observed="$(
  for invf in inventory/proxmox-*.json; do
    [ -e "${invf}" ] || continue
    node="$(node_of "${invf}")"
    jq -r --arg n "${node}" '.pools[]? | "\($n)\t\(.poolid)"' "${invf}"
  done | sort
)"
if [ "${declared}" != "${observed}" ]; then
  violation "pool-set drift — declared (invariants.json) vs observed (inventory) differ:"
  diff <(printf '%s\n' "${declared}") <(printf '%s\n' "${observed}") >&2 || true
  echo "      (changing the declared set is a docs/system-design.md PR — it is the dial)" >&2
fi
[ "${fail}" -eq "${before}" ] && ok "observed pool set == declared set"

# --- 3. No plaintext secret patterns in tracked, non-encrypted files ---------------------------
echo "== no plaintext secret patterns in tracked files =="
before=${fail}
excludes=()
while IFS= read -r glob; do
  [ -n "${glob}" ] && excludes+=(":(exclude)${glob}" ":(exclude)**/${glob}")
done < <(jq -r '.secret_patterns.allow[].glob' "${INV}")
while IFS= read -r pat; do
  [ -n "${pat}" ] || continue
  hits="$(git grep -nIE -e "${pat}" -- . "${excludes[@]}" 2>/dev/null || true)"
  if [ -n "${hits}" ]; then
    violation "secret pattern /${pat}/ matched tracked file(s):"
    printf '%s\n' "${hits}" | sed 's/^/        /' >&2
  fi
done < <(jq -r '.secret_patterns.patterns[].pattern' "${INV}")
[ "${fail}" -eq "${before}" ] && ok "no plaintext secret patterns found in tracked files"

# --- 4. Every running entity is mapped or a declared exception (SKY-018 L0) ---------------------
# The entity audit IS the checker for this law (one implementation, not two): it derives every
# guest/service, joins against observed firewall/DNS/compose truth, and exits non-zero on a running
# entity that is neither mapped nor a declared exception (invariants.json entity_conventions /
# excluded_guests). Reuse it rather than re-implementing the join here.
echo "== every running entity is mapped or a declared exception (SKY-018) =="
before=${fail}
if audit_out="$(./scripts/audit-entities.sh 2>&1)"; then
  ok "every running guest & service is mapped or a declared exception"
else
  violation "running entities with no home — map each (a firewall/DNS host fact, or a compose/<svc>/ dir) or declare it in invariants.json entity_conventions.exceptions:"
  printf '%s\n' "${audit_out}" | grep -E 'running-unmapped' | sed 's/^/        /' >&2
fi

# --- 5. Operate-token ACL never crosses the bright lines / self-provisions off-node (SKY-021) ----
# The checker for the /vms-root widening: read each node's collected operate-token ACL and assert
# (1) NO forbidden privilege at any path (Permissions.Modify = self-leash rewrite; Sys.Modify/
# PowerMgmt/Console = node root), (2) node-root VM allocation only on declared vms_root_nodes.
echo "== operate-token ACL holds the bright lines (no self-leash / node-root; /vms-root only where declared) =="
before=${fail}
mapfile -t forbidden < <(jq -r '.operate_token_scope.forbidden_privileges[]' "${INV}")
mapfile -t vms_root_nodes < <(jq -r '.operate_token_scope.vms_root_nodes[].node' "${INV}")
forbidden_json="$(jq -c '.operate_token_scope.forbidden_privileges' "${INV}")"
acl_seen=0
for aclf in inventory/proxmox-*-acl.json; do
  [ -e "${aclf}" ] || continue
  acl_seen=1
  anode="$(jq -r '.node // "?"' "${aclf}")"
  # (1) any forbidden privilege at any path → violation (path:priv listed)
  while IFS= read -r hit; do
    [ -n "${hit}" ] && violation "${anode}: operate token holds bright-line privilege ${hit} — never standing (constitution §2/§6); revoke via pveum"
  done < <(jq -r --argjson f "${forbidden_json}" \
    '[.permissions | to_entries[] as $e | $f[] as $p | select($e.value[$p]==1) | "\($e.key)=\($p)"] | unique | .[]' "${aclf}")
  # (2) node-root VM.Allocate (/ or /vms) allowed only on a declared vms_root node
  roots="$(jq -r '[.permissions | to_entries[] | select((.key=="/" or .key=="/vms") and (.value["VM.Allocate"]==1)) | .key] | join(",")' "${aclf}")"
  if [ -n "${roots}" ]; then
    allowed=0; for n in "${vms_root_nodes[@]}"; do [ "${n}" = "${anode}" ] && allowed=1; done
    [ "${allowed}" -eq 1 ] \
      || violation "${anode}: operate token has node-root VM.Allocate (${roots}) but ${anode} is not a declared vms_root_node — a /vms grant off the declared node is a docs/system-design.md PR, not a silent pveum"
  fi
done
if [ "${acl_seen}" -eq 0 ]; then
  ok "no proxmox-*-acl.json in inventory yet — acl audit idle (run scripts/collect-proxmox-acl.sh)"
elif [ "${fail}" -eq "${before}" ]; then
  ok "operate token: no bright-line privilege anywhere; /vms-root only on declared node(s) [${vms_root_nodes[*]}]"
fi

# --- 6. Construction helpers stay within their declared build-time leash (SKY-022) --------------
echo "== construction helper cap and sandboxes match the declared build-time leash =="
before=${fail}
declared_cap="$(jq -r '.construction.max_concurrent_threads_per_session' "${INV}")"
forbidden_sandbox="$(jq -r '.construction.forbidden_sandbox_mode' "${INV}")"
config_file=".codex/config.toml"
if [ ! -r "${config_file}" ]; then
  violation "${config_file} is missing — declare max_concurrent_threads_per_session = ${declared_cap} under [agents]"
else
  cap_line="$(grep -E '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' "${config_file}" || true)"
  found_cap="$(printf '%s\n' "${cap_line}" | sed -nE 's/^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=[[:space:]]*([^[:space:]#]+).*/\1/p' | head -n 1)"
  if [ -z "${found_cap}" ]; then
    violation "${config_file} has no max_concurrent_threads_per_session declaration — expected ${declared_cap}"
  elif [ "${found_cap}" != "${declared_cap}" ]; then
    violation "${config_file}: max_concurrent_threads_per_session is ${found_cap} — expected ${declared_cap} from invariants.json"
  fi
fi

while IFS=$'\t' read -r role expected_sandbox; do
  agent_file=".codex/agents/${role}.toml"
  if [ ! -r "${agent_file}" ]; then
    violation "${role}: ${agent_file} is missing — declare sandbox_mode = \"${expected_sandbox}\""
    continue
  fi
  sandbox_line="$(grep -E '^[[:space:]]*sandbox_mode[[:space:]]*=' "${agent_file}" || true)"
  found_sandbox="$(printf '%s\n' "${sandbox_line}" | sed -nE 's/^[[:space:]]*sandbox_mode[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' | head -n 1)"
  if [ -z "${found_sandbox}" ]; then
    violation "${role}: ${agent_file} has no sandbox_mode declaration — expected \"${expected_sandbox}\""
  elif [ "${found_sandbox}" != "${expected_sandbox}" ]; then
    violation "${role}: ${agent_file} declares sandbox_mode = \"${found_sandbox}\" — expected \"${expected_sandbox}\" from invariants.json"
  fi
done < <(jq -r '.construction.agents[] | "\(.role)\t\(.sandbox_mode)"' "${INV}")

for agent_file in .codex/agents/*.toml; do
  [ -e "${agent_file}" ] || continue
  sandbox_line="$(grep -E '^[[:space:]]*sandbox_mode[[:space:]]*=' "${agent_file}" || true)"
  found_sandbox="$(printf '%s\n' "${sandbox_line}" | sed -nE 's/^[[:space:]]*sandbox_mode[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' | head -n 1)"
  if [ "${found_sandbox}" = "${forbidden_sandbox}" ]; then
    violation "${agent_file} declares forbidden sandbox_mode = \"${forbidden_sandbox}\" — a construction helper must never receive danger-full-access"
  fi
done
[ "${fail}" -eq "${before}" ] && ok "construction cap is ${declared_cap}; declared helper sandboxes match; no helper has forbidden ${forbidden_sandbox}"

echo
if [ "${fail}" -ne 0 ]; then
  echo "check-invariants: FAILED — a hard law is violated (see ✗ above). This PR must not land." >&2
  exit 1
fi
echo "check-invariants: OK — all machine-checkable hard laws hold."
