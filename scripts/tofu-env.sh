#!/usr/bin/env bash
# tofu-env.sh — export env vars for OpenTofu from sops-nix decrypted secrets.
# TIER: T2 — reads the svc-tofu API tokens (pool-scoped, privilege-separated) for BOTH Proxmox
# nodes (standalone, not clustered → one token each). USAGE: eval "$(scripts/tofu-env.sh)".
#   Reads: /opt/skynet-ops/secrets/tofu-proxmox.env          (core node .11)
#          /opt/skynet-ops/secrets/tofu-proxmox-network.env  (network node .10)
#          /opt/skynet-ops/secrets/tofu-passphrase           (state encryption passphrase)
#   Builds a combined CA bundle (both nodes' pinned certs) and points SSL_CERT_FILE at it.
set -euo pipefail

SECRETS_DIR="${SECRETS_DIR:-/opt/skynet-ops/secrets}"
CERTS_DIR="${CERTS_DIR:-/opt/skynet-ops/certs}"

pass_file="${SECRETS_DIR}/tofu-passphrase"
core_file="${SECRETS_DIR}/tofu-proxmox.env"
net_file="${SECRETS_DIR}/tofu-proxmox-network.env"

for f in "${pass_file}" "${core_file}" "${net_file}"; do
  [ -f "${f}" ] || { echo "missing ${f} — is sops-nix decryption working? (nixos-rebuild)" >&2; exit 1; }
done

# Source each dotenv in turn (they share TOFU_PVE_* names) and capture into node-specific vars.
set -a
# shellcheck source=/dev/null
. "${core_file}"; CORE_HOST="${TOFU_PVE_HOST}"; CORE_TOKEN="${TOFU_PVE_TOKEN}"; CORE_CACERT="${TOFU_PVE_CACERT:-${CERTS_DIR}/proxmox-core.crt}"
# shellcheck source=/dev/null
. "${net_file}";  NET_HOST="${TOFU_PVE_HOST}";  NET_TOKEN="${TOFU_PVE_TOKEN}";  NET_CACERT="${TOFU_PVE_CACERT:-${CERTS_DIR}/proxmox-network.crt}"
set +a

passphrase="$(cat "${pass_file}")"

# Combined CA bundle — Go/OpenSSL SSL_CERT_FILE is a single file, so concatenate both pinned certs.
bundle="${HOME}/.cache/skynet/tofu-ca-bundle.crt"
mkdir -p "$(dirname "${bundle}")"
cat "${CORE_CACERT}" "${NET_CACERT}" > "${bundle}"

cat <<EOF
export TF_VAR_proxmox_endpoint='https://${CORE_HOST}:8006'
export TF_VAR_proxmox_api_token='${CORE_TOKEN}'
export TF_VAR_proxmox_endpoint_network='https://${NET_HOST}:8006'
export TF_VAR_proxmox_api_token_network='${NET_TOKEN}'
export TF_VAR_state_passphrase='${passphrase}'
export SSL_CERT_FILE='${bundle}'
EOF
