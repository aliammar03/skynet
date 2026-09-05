#!/usr/bin/env bash
# skynet-ops-ssh-certs.sh — runs ON vm-skynet-ops. Regenerates host-specific ssh_config
# entries from ~/.ssh/certs/*-cert.pub, so `ssh root@<host>` presents only that host's cert
# and multiple grants coexist (access-and-trust.md — SSH user-CA).
#
# grant-root calls this after placing a cert; it's idempotent, so re-running is safe. It scopes
# the certs to their named hosts only, leaving svc-ops (T1) connections untouched.
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
    host="$(basename "${c}" -cert.pub)"
    # A fleet-wide grant is the one safe exception to host-specific selection. All other
    # grants must be selected by the exact SSH host alias; offering every cert can exhaust
    # MaxAuthTries before the matching certificate is attempted.
    if [ "${host}" = "all" ]; then
      echo "Host *"
    else
      echo "Host ${host}"
    fi
    echo "    User root"
    echo "    IdentityFile ~/.ssh/id_ed25519"
    echo "    CertificateFile ~/.ssh/certs/$(basename "${c}")"
    n=$((n+1))
  done
  echo "${E}"
} >> "${cfg}"
echo "refreshed ${cfg}: ${n} host-scoped root cert file(s)"
