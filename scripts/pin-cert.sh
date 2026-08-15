#!/usr/bin/env bash
# pin-cert.sh — capture an internal endpoint's TLS cert chain for pinning (T1, no remote root).
# Skynet's internal APIs (Proxmox, PBS, Technitium) serve self-signed / private-CA certs.
# Rather than disable verification (-k), collectors verify with curl --cacert against the
# exact chain captured here (trust-on-first-use). Re-pin if an endpoint's cert is rotated.
#
# A server certificate is PUBLIC material, not a secret: pins live in /opt/skynet-ops/certs/
# (dir 0755, files 0644 — readable by the svc-ops/ali user that runs the collectors), NOT in
# /opt/skynet-ops/secrets/ (which is root-only and holds tokens/keys).
#
# USAGE: pin-cert.sh <host> <port> <out.pem>
#   e.g. pin-cert.sh 10.10.50.10 8006 /opt/skynet-ops/certs/proxmox-core.crt
set -euo pipefail
host="${1:?usage: pin-cert.sh <host> <port> <out.pem>}"
port="${2:?port}"
out="${3:?out.pem}"

command -v openssl >/dev/null || { echo "openssl required" >&2; exit 1; }

tmp="$(mktemp)"; trap 'rm -f "${tmp}"' EXIT
# -showcerts emits every cert the server presents (leaf + any intermediates/CA).
openssl s_client -connect "${host}:${port}" -servername "${host}" -showcerts </dev/null 2>/dev/null \
  | awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/' > "${tmp}"

grep -q 'BEGIN CERTIFICATE' "${tmp}" || { echo "no certificate captured from ${host}:${port}" >&2; exit 1; }

outdir="$(dirname "${out}")"
[ -d "${outdir}" ] || sudo install -d -m 0755 -o root -g root "${outdir}"
if [ -w "${outdir}" ]; then
  install -m 0644 "${tmp}" "${out}"
else
  sudo install -m 0644 -o root -g root "${tmp}" "${out}"
fi

echo "pinned $(grep -c 'BEGIN CERTIFICATE' "${out}") cert(s) → ${out} (0644, public)"
echo "SHA-256 fingerprint(s):"
openssl crl2pkcs7 -nocrl -certfile "${out}" \
  | openssl pkcs7 -print_certs 2>/dev/null \
  | openssl x509 -noout -fingerprint -sha256 2>/dev/null \
  || openssl x509 -in "${out}" -noout -fingerprint -sha256
