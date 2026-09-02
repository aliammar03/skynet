#!/usr/bin/env bash
# skynet-ops-ssh-certs.sh — runs ON vm-skynet-ops. Regenerates the "Match user root" block in
# ~/.ssh/config from the per-host certs in ~/.ssh/certs/*.pub (+ the legacy single cert), so
# `ssh root@<host>` presents the RIGHT cert and multiple host grants coexist (access-and-trust.md — SSH user-CA).
#
# grant-root calls this after placing a cert; it's idempotent, so re-running is safe. It scopes
# the certs to root logins only (Match user root), leaving svc-ops (T1) connections untouched.
set -euo pipefail
cfg="${HOME}/.ssh/config"; certs="${HOME}/.ssh/certs"
S="# >>> skynet-ops root certs (managed by scripts/skynet-ops-ssh-certs.sh — do not edit inside)"
E="# <<< skynet-ops root certs"
mkdir -p "${certs}"; chmod 700 "${HOME}/.ssh" "${certs}"; touch "${cfg}"; chmod 600 "${cfg}"

# Strip any existing managed block (markers + contents).
awk -v s="${S}" -v e="${E}" '
  $0==s {skip=1; next}
  $0==e {skip=0; next}
  skip!=1 {print}
' "${cfg}" > "${cfg}.tmp" && mv "${cfg}.tmp" "${cfg}"

# Append a fresh block from whatever certs currently exist.
n=0
{
  echo "${S}"
  echo "Match user root"
  echo "    IdentityFile ~/.ssh/id_ed25519"
  if [ -f "${HOME}/.ssh/id_ed25519-cert.pub" ]; then echo "    CertificateFile ~/.ssh/id_ed25519-cert.pub"; n=$((n+1)); fi
  for c in "${certs}"/*-cert.pub; do
    [ -e "${c}" ] || continue
    # Prune certs whose validity window has already closed: they'd be refused by sshd anyway,
    # and left in place they accumulate forever until `ssh root@host` exhausts MaxAuthTries
    # offering dead certs before reaching a live one. Non-expiring certs ("forever") are kept.
    valid_to="$(ssh-keygen -L -f "${c}" 2>/dev/null | awk '/^ *Valid:/{print $NF}')"
    exp="$(date -d "${valid_to}" +%s 2>/dev/null || echo 0)"
    if [ "${exp}" -ne 0 ] && [ "${exp}" -lt "$(date +%s)" ]; then
      rm -f "${c}"; echo "pruned expired cert $(basename "${c}")" >&2; continue
    fi
    echo "    CertificateFile ~/.ssh/certs/$(basename "${c}")"; n=$((n+1))
  done
  echo "${E}"
} >> "${cfg}"
echo "refreshed ${cfg}: ${n} root cert file(s) presented for 'ssh root@<host>'"
