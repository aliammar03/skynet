#!/usr/bin/env bash
# bootstrap-workstation.sh — one-time setup on ALI'S WORKSTATION (plan §8)
# TIER: CA custody — HUMAN RUNS THIS on the workstation, never on the VM.
#   The SSH user-CA private key is the whole security model: it must exist ONLY here.
# USAGE: bootstrap-workstation.sh
# RESULT: creates the CA, installs bin/grant-root as ~/bin/grant-root, adds the `gr` alias.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CA_DIR="${HOME}/.skynet-ca"
CA_KEY="${CA_DIR}/ops_ca"

if [ -f "${CA_KEY}" ]; then
  echo "CA already exists at ${CA_KEY} (leaving it untouched)."
else
  echo "==> creating passphrase-protected SSH user-CA at ${CA_KEY}"
  echo "    Choose a strong passphrase and copy it to your password manager."
  mkdir -p "${CA_DIR}" && chmod 700 "${CA_DIR}"
  ssh-keygen -t ed25519 -f "${CA_KEY}" -C "skynet-ops-ca"
  echo "==> ALSO back up ${CA_KEY} (private) to your password manager + printed survival kit."
fi

echo "==> installing grant-root to ~/bin/grant-root"
mkdir -p "${HOME}/bin"
install -m 755 "${REPO_DIR}/bin/grant-root" "${HOME}/bin/grant-root"

RC="${HOME}/.bashrc"; [ -n "${ZSH_VERSION:-}" ] && RC="${HOME}/.zshrc"
if ! grep -q "alias gr=" "${RC}" 2>/dev/null; then
  echo "alias gr='~/bin/grant-root'" >> "${RC}"
  echo "==> added 'gr' alias to ${RC} (open a new shell to use it)"
else
  echo "==> 'gr' alias already present in ${RC}"
fi

echo
echo "The CA public key to onboard hosts with:"
ssh-keygen -y -f "${CA_KEY}" 2>/dev/null || echo "(re-run after unlocking the key)"
echo "Copy the .pub next to onboard-host.sh as skynet_ops_ca.pub when onboarding a host."
