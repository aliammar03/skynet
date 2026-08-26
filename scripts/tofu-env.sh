#!/usr/bin/env bash
# tofu-env.sh — export env vars for OpenTofu from sops-nix decrypted secrets.
# TIER: T2 — reads the svc-tofu API token (pool-scoped, privilege-separated).
# USAGE: eval "$(scripts/tofu-env.sh)"   then:  cd tofu && tofu plan
#   Reads: /opt/skynet-ops/secrets/tofu-proxmox.env  (TOFU_PVE_HOST, TOFU_PVE_TOKEN, TOFU_PVE_CACERT)
#          /opt/skynet-ops/secrets/tofu-passphrase    (state encryption passphrase)
#   Also sets SSL_CERT_FILE for pinned Proxmox TLS.
set -euo pipefail

SECRETS_DIR="${SECRETS_DIR:-/opt/skynet-ops/secrets}"

token_file="${SECRETS_DIR}/tofu-proxmox.env"
pass_file="${SECRETS_DIR}/tofu-passphrase"

[ -f "${token_file}" ] || { echo "missing ${token_file} — is sops-nix decryption working?" >&2; exit 1; }
[ -f "${pass_file}" ]  || { echo "missing ${pass_file} — is sops-nix decryption working?" >&2; exit 1; }

# Source the dotenv to get TOFU_PVE_HOST, TOFU_PVE_TOKEN, TOFU_PVE_CACERT
set -a
# shellcheck source=/dev/null
. "${token_file}"
set +a

passphrase="$(cat "${pass_file}")"

cat <<EOF
export TF_VAR_proxmox_endpoint='https://${TOFU_PVE_HOST}:8006'
export TF_VAR_proxmox_api_token='${TOFU_PVE_TOKEN}'
export TF_VAR_state_passphrase='${passphrase}'
export SSL_CERT_FILE='${TOFU_PVE_CACERT:-/opt/skynet-ops/certs/proxmox-core.crt}'
EOF
