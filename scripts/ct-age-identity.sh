#!/usr/bin/env bash
# ct-age-identity.sh — per-CT age identity for pool NixOS LXCs (SKY-021 P3, "Option C").
#
# THE PROBLEM this solves. A pool CT decrypts its own service secrets with sops-nix at activation,
# so it needs an age *private* key on the box. Using the CT's ephemeral ssh host key (what P2 proved)
# breaks the "rebuild from git alone" invariant: destroy+recreate mints a NEW host key → a NEW
# recipient → every secret in git encrypted to the OLD one is undecryptable. And copying the LAB
# master key onto every CT spreads the crown-jewel (one popped CT = the whole secret world).
#
# OPTION C — a two-tier key hierarchy that keeps BOTH invariants:
#   lab master age key (survival kit + ops VM)  ──decrypts──▶  per-CT age key (this script; encrypted
#   to the lab key, COMMITTED in git)  ──decrypts──▶  that CT's service secrets (encrypted to BOTH the
#   lab key AND the CT recipient, so ops/Ali can always read them too).
# Recreate = re-INJECT the same per-CT key → the git ciphertext stays valid, no re-encryption, no
# master key on the CT. Blast radius of a popped CT = that one CT's secrets, not the lab.
#
# Files per host <h> (both COMMITTED — the .pub is public, the .sops is lab-encrypted):
#   secrets/<h>-age.pub        the CT's age recipient (plaintext; used in .sops.yaml + the host's
#                              sops.age config, and to encrypt that host's service secrets to it)
#   secrets/<h>-age.key.sops   the CT's age PRIVATE key, sops-encrypted to the LAB key (bootstrap
#                              secret; injected at provision). Matches the `*-age.key.sops` rule.
#
# USAGE
#   ct-age-identity.sh new    <host>              # mint the identity (idempotent-safe: refuses to clobber)
#   ct-age-identity.sh pubkey <host>              # print the CT recipient (from the committed .pub)
#   ct-age-identity.sh inject <host> <ssh-target> # decrypt (lab key) → install to the CT, no plaintext on disk
#
# The lab key is read from sops.age.keyFile on the ops VM (SOPS_AGE_KEY_FILE override respected).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_KEY="${SOPS_AGE_KEY_FILE:-/nix/persist/opt/skynet-ops/secrets/age.key}"
# Where sops-nix on the CT reads its identity (nix/modules/lxc-base.nix points sops.age.keyFile here).
CT_KEYFILE="/var/lib/sops-nix/age.key"

die() { echo "ct-age-identity: $*" >&2; exit 1; }

secrets_dir="${REPO_DIR}/secrets"

cmd_new() {
  local h="${1:?usage: ct-age-identity.sh new <host>}"
  local sops_file="${secrets_dir}/${h}-age.key.sops"
  local pub_file="${secrets_dir}/${h}-age.pub"
  [ -e "${sops_file}" ] && die "${sops_file#${REPO_DIR}/} already exists — refusing to overwrite an identity in use (rm it deliberately to rotate)"

  # Generate in a private tmpdir; the plaintext key never lands in the repo or a world path.
  local tmp; tmp="$(mktemp -d)"; trap 'rm -rf "${tmp}"' RETURN
  ( umask 077; age-keygen -o "${tmp}/key" 2>/dev/null )
  local pub; pub="$(age-keygen -y "${tmp}/key")"

  printf '%s\n' "${pub}" > "${pub_file}"
  # Encrypt the private half to the LAB key. --filename-override makes sops apply the repo
  # .sops.yaml rule for `secrets/<h>-age.key.sops` (lab-only) even though the input is a tmp path.
  sops encrypt --filename-override "secrets/${h}-age.key.sops" \
       --input-type binary --output-type binary "${tmp}/key" > "${sops_file}"

  echo "minted ${h}: recipient ${pub}"
  echo "  wrote ${pub_file#${REPO_DIR}/} (committed) + ${sops_file#${REPO_DIR}/} (lab-encrypted, committed)"
  cat <<EOF

Next: add a .sops.yaml creation rule so ${h}'s SERVICE secrets go to BOTH the lab key and this CT
(dual-recipient — the CT decrypts at activation, ops/Ali can always read too). Put it ABOVE the
generic \`secrets/.*\\.sops\$\` rule (first match wins):

  - path_regex: secrets/${h}/.*\\.sops\$
    age: >-
      age1stah9c426pq0xf3k4qc58e92vs263lf6uvze2f6nmx84nvk86cusfgexyw,
      ${pub}

Then in the host's flake config: sops.age.keyFile = "${CT_KEYFILE}";
and at provision, before the first deploy: ct-age-identity.sh inject ${h} root@<ct-ip>
EOF
}

cmd_pubkey() {
  local h="${1:?usage: ct-age-identity.sh pubkey <host>}"
  local pub_file="${secrets_dir}/${h}-age.pub"
  [ -r "${pub_file}" ] || die "no identity for ${h} (${pub_file#${REPO_DIR}/} missing) — run: ct-age-identity.sh new ${h}"
  cat "${pub_file}"
}

cmd_inject() {
  local h="${1:?usage: ct-age-identity.sh inject <host> <ssh-target>}"
  local target="${2:?usage: ct-age-identity.sh inject <host> <ssh-target>}"
  local sops_file="${secrets_dir}/${h}-age.key.sops"
  [ -r "${sops_file}" ] || die "no identity for ${h} (${sops_file#${REPO_DIR}/} missing) — run: ct-age-identity.sh new ${h}"
  [ -r "${LAB_KEY}" ] || die "lab age key ${LAB_KEY} not readable — cannot decrypt the per-CT identity"

  # Decrypt with the lab key and STREAM it into the CT over ssh — the plaintext per-CT key never
  # touches the ops VM's disk. install(1) creates the dir + file 0400 root in one shot.
  SOPS_AGE_KEY_FILE="${LAB_KEY}" sops decrypt --input-type binary --output-type binary "${sops_file}" \
    | ssh -o BatchMode=yes "${target}" "install -m 0400 -o root -g root -D /dev/stdin ${CT_KEYFILE}" \
    || die "inject failed (ssh to ${target}? key at ${sops_file#${REPO_DIR}/} decryptable?)"
  echo "injected ${h} identity → ${target}:${CT_KEYFILE} (0400 root)"
}

case "${1:-}" in
  new)    shift; cmd_new "$@" ;;
  pubkey) shift; cmd_pubkey "$@" ;;
  inject) shift; cmd_inject "$@" ;;
  *) die "usage: ct-age-identity.sh {new|pubkey|inject} <host> [ssh-target]" ;;
esac
