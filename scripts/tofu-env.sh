#!/usr/bin/env bash
# tofu-env.sh — export env vars for OpenTofu from sops-nix decrypted secrets.
# TIER: T2 — reads the Proxmox API tokens for BOTH nodes (standalone, not clustered → one token each).
# SKY-024 retired the svc-tofu split: tofu now runs as the ONE operator token on each node
# (svc-ops@pve!operate, full VM/Datastore/Pool/SDN at /, bright lines held), the same identity the
# imperative ops scripts use — so declare + fix is one token, not a per-capability grant dance. Core
# is root-ACL broadened; network remains pool-scoped. USAGE: eval "$(scripts/tofu-env.sh)".
#   Reads: /opt/skynet-ops/secrets/proxmox-core.env          (core node .11 — operate token)
#          /opt/skynet-ops/secrets/proxmox-network.env       (network node .10 — operate, pool-scoped)
#          /opt/skynet-ops/secrets/tofu-passphrase           (state encryption passphrase)
#          /opt/skynet-ops/secrets/technitium.env            (T2 zones-only DNS token, SKY-008 P3)
#          /opt/skynet-ops/secrets/cloudflare-dns.env        (T2 Zone:DNS:Edit token, SKY-014 public DNS)
#   Optional scope: state|proxmox-core|proxmox-network|technitium-dns|cloudflare-dns|all (default).
#   A saved-plan apply loads only its declared actuator credentials after first loading `state` to
#   decrypt and inspect the plan. Plan creation from the legacy combined root still uses `all`.
#   Builds a combined CA bundle (both nodes' + Technitium's pinned certs) and points SSL_CERT_FILE
#   at it, so the technitium provider (which offers no cacert arg) verifies its self-signed cert.
set -euo pipefail

scope="${1:-all}"
case "${scope}" in state|proxmox-core|proxmox-network|technitium-dns|cloudflare-dns|all) : ;;
  *) echo "usage: tofu-env.sh [state|proxmox-core|proxmox-network|technitium-dns|cloudflare-dns|all]" >&2; exit 2;; esac

SECRETS_DIR="${SECRETS_DIR:-/opt/skynet-ops/secrets}"
CERTS_DIR="${CERTS_DIR:-/opt/skynet-ops/certs}"

pass_file="${SECRETS_DIR}/tofu-passphrase"
# SKY-024: one operator token per node — tofu runs as svc-ops!operate on BOTH (the svc-tofu split is
# retired). Core is /-broadened (can mint VMIDs); network stays pool-scoped by design — OPNsense (the
# leash-enforcing firewall) lives there, so no /vms-root envelope-destroy over it.
core_file="${SECRETS_DIR}/proxmox-core.env"
net_file="${SECRETS_DIR}/proxmox-network.env"
tech_file="${SECRETS_DIR}/technitium.env"
cf_file="${SECRETS_DIR}/cloudflare-dns.env"

need() { [ -f "$1" ] || { echo "missing $1 — is sops-nix decryption working? (nixos-rebuild)" >&2; exit 1; }; }
need "${pass_file}"
passphrase="$(cat "${pass_file}")"
if [ "${scope}" = state ]; then
  printf "export TF_VAR_state_passphrase='%s'\n" "${passphrase}"
  exit 0
fi

case "${scope}" in
  proxmox-core) need "${core_file}" ;;
  proxmox-network) need "${net_file}" ;;
  technitium-dns) need "${tech_file}" ;;
  cloudflare-dns) : ;;
  all) need "${core_file}"; need "${net_file}"; need "${tech_file}" ;;
esac

# Source each operate-token dotenv in turn and capture into node-specific vars.
set -a
if [ "${scope}" = proxmox-core ] || [ "${scope}" = all ]; then
  # shellcheck source=/dev/null
  . "${core_file}"; CORE_HOST="${PVE_HOST}"; CORE_TOKEN="${PVE_TOKEN_OPERATE}"; CORE_CACERT="${PVE_CACERT:-${CERTS_DIR}/proxmox-core.crt}"
fi
if [ "${scope}" = proxmox-network ] || [ "${scope}" = all ]; then
  # shellcheck source=/dev/null
  . "${net_file}"; NET_HOST="${PVE_HOST}"; NET_TOKEN="${PVE_TOKEN_OPERATE}"; NET_CACERT="${PVE_CACERT:-${CERTS_DIR}/proxmox-network.crt}"
fi
if [ "${scope}" = technitium-dns ] || [ "${scope}" = all ]; then
  # shellcheck source=/dev/null
  . "${tech_file}"; TECH_CACERT="${TECH_CACERT:-${CERTS_DIR}/technitium.crt}"
fi
if [ "${scope}" = cloudflare-dns ] || [ "${scope}" = all ]; then
  # cloudflare-dns.env is root-owned (not sops-nix) → read with a sudo fallback.
  # shellcheck disable=SC1090
  source <(cat "${cf_file}" 2>/dev/null || sudo -n cat "${cf_file}" 2>/dev/null || true)
  [ -n "${CF_DNS_TOKEN:-}" ] || { echo "missing/unreadable ${cf_file} (CF_DNS_TOKEN) — 0600 root; scoped Zone:DNS:Edit token" >&2; exit 1; }
fi
set +a

# Technitium's provider has no per-provider CA argument, so only its scope needs SSL_CERT_FILE.
bundle="${HOME}/.cache/skynet/tofu-ca-bundle.crt"
if [ "${scope}" = technitium-dns ] || [ "${scope}" = all ]; then
  mkdir -p "$(dirname "${bundle}")"
  if [ "${scope}" = all ]; then
    cat "${CORE_CACERT}" "${NET_CACERT}" "${TECH_CACERT}" > "${bundle}"
  else
    cat "${TECH_CACERT}" > "${bundle}"
  fi
fi

# NB: technitium url OMITS /api — the provider client prepends it (a `.../api` url double-paths → EOF).
cat <<EOF
export TF_VAR_state_passphrase='${passphrase}'
EOF
if [ "${scope}" = proxmox-core ] || [ "${scope}" = all ]; then
  printf "export TF_VAR_proxmox_endpoint='https://%s:8006'\nexport TF_VAR_proxmox_api_token='%s'\n" "${CORE_HOST}" "${CORE_TOKEN}"
fi
if [ "${scope}" = proxmox-network ] || [ "${scope}" = all ]; then
  printf "export TF_VAR_proxmox_endpoint_network='https://%s:8006'\nexport TF_VAR_proxmox_api_token_network='%s'\n" "${NET_HOST}" "${NET_TOKEN}"
fi
if [ "${scope}" = technitium-dns ] || [ "${scope}" = all ]; then
  printf "export TF_VAR_technitium_url='https://%s:53443'\nexport TF_VAR_technitium_api_token='%s'\nexport SSL_CERT_FILE='%s'\n" "${TECH_HOST}" "${TECH_TOKEN}" "${bundle}"
fi
if [ "${scope}" = cloudflare-dns ] || [ "${scope}" = all ]; then
  printf "export TF_VAR_cloudflare_api_token='%s'\nexport TF_VAR_cloudflare_tunnel_id='%s'\n" "${CF_DNS_TOKEN}" "${TUNNEL_ID}"
fi
