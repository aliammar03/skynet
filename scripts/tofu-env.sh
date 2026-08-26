#!/usr/bin/env bash
# tofu-env.sh — decrypt sops secrets and export env vars for OpenTofu.
# TIER: T2 — reads the svc-tofu API token (pool-scoped, privilege-separated).
# USAGE: eval "$(scripts/tofu-env.sh)"   then:  cd tofu && tofu plan
#   Reads: secrets/tofu-proxmox.env.sops   (API token)
#          secrets/tofu-passphrase.sops     (state encryption passphrase)
#   Also sets SSL_CERT_FILE for pinned Proxmox TLS.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-/opt/skynet-ops/secrets/age.key}"

token_file="${REPO_DIR}/secrets/tofu-proxmox.env.sops"
pass_file="${REPO_DIR}/secrets/tofu-passphrase.sops"

[ -f "${token_file}" ] || { echo "missing ${token_file}" >&2; exit 1; }
[ -f "${pass_file}" ]  || { echo "missing ${pass_file}" >&2; exit 1; }

eval "$(sops -d --output-type dotenv "${token_file}")"
passphrase="$(sops -d --extract '["passphrase"]' "${pass_file}")"

cat <<EOF
export TF_VAR_proxmox_endpoint='https://${TOFU_PVE_HOST}:8006'
export TF_VAR_proxmox_api_token='${TOFU_PVE_TOKEN}'
export TF_VAR_state_passphrase='${passphrase}'
export SSL_CERT_FILE='${TOFU_PVE_CACERT:-/opt/skynet-ops/certs/proxmox-core.crt}'
EOF
