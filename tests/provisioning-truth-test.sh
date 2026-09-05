#!/usr/bin/env bash
# provisioning-truth-test.sh — keep the audited provisioning/trust boundary explicit and current.
# TIER: T1 — reads tracked text only; no OpenTofu plan, secrets, or infrastructure access.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  \342\234\223 %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \342\234\227 %s\n' "$1" >&2; fail=$((fail+1)); }

cts="tofu/pool-cts.tf"
native="$(awk '/resource "proxmox_virtual_environment_container" "core_ct"/{on=1} on{print}' "${cts}")"

rg -q 'imported_core_cts' "${cts}" && ok "imported CT compatibility map is explicit" || bad "missing imported CT map"
rg -q 'native_core_cts' "${cts}" && ok "native core CT map is explicit" || bad "missing native CT map"
printf '%s\n' "${native}" | rg -q '^resource "proxmox_virtual_environment_container" "core_ct"' \
  && ok "native CT resource exists" || bad "missing native CT resource"
printf '%s\n' "${native}" | rg -q 'lifecycle \{' \
  && bad "native CT resource inherited lifecycle ignores" || ok "native CT day-two fields are not ignored"
printf '%s\n' "${native}" | rg -q 'pool_id' \
  && bad "native core CT unexpectedly claims pool membership" || ok "native core CT is honestly unpooled"

rg -Uq 'PBS CT 240 is an existing\n   `ops-managed` import, not an excluded guest' runbooks/provision-lxc.md \
  && ok "LXC runbook distinguishes PBS import from excluded guests" || bad "LXC runbook still calls PBS excluded"
rg -q 'scoped Authentik Applications/Providers' AGENTS.md \
  && ok "always-loaded trust table exposes Authentik T2 carve-out" || bad "Authentik T2 carve-out missing from AGENTS"
rg -q 'temporary bootstrap SSH key' runbooks/provision-vm.md \
  && ok "VM runbook requires bootstrap onboarding" || bad "VM runbook overclaims baked onboarding"

current_directive="$(sed '/^## 6\. Status log/,$d' planning/projects/SKY-024-tofu-declares-all-pool-guests-api-driven-ct-vm-lifecycle-no-node-ssh.md)"
printf '%s\n' "${current_directive}" | rg -q 'current_phase: 4' \
  && ok "SKY-024 points to the next unfinished phase" || bad "SKY-024 phase pointer is stale"
printf '%s\n' "${current_directive}" | rg -q '`tofu apply`|`tofu destroy`' \
  && bad "active SKY-024 instructions retain bare apply/destroy" || ok "active SKY-024 uses current wrapper semantics"

echo
echo "provisioning-truth-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
