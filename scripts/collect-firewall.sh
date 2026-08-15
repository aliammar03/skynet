#!/usr/bin/env bash
# collect-firewall.sh — parse the mirrored OPNsense config.xml → inventory/firewall/*.json
# USAGE: collect-firewall.sh [path-to-config.xml]
#   Truth source is the skynet-opnsense repo (os-git-backup auto-pushes config.xml, branch
#   master). NO management-plane access — we read the git mirror, never OPNsense itself (T3).
#   Default mirror: /opt/skynet-ops/mirror/skynet-opnsense/config.xml
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cfg="${1:-/opt/skynet-ops/mirror/skynet-opnsense/config.xml}"
outdir="${REPO_DIR}/inventory/firewall"
mkdir -p "${outdir}"

# Refresh the mirror if it is a git checkout (best-effort; never fail the collector on it).
mirror_dir="$(dirname "${cfg}")"
if [ -d "${mirror_dir}/.git" ]; then
  git -C "${mirror_dir}" pull --quiet --ff-only 2>/dev/null || echo "warn: mirror pull skipped" >&2
fi

if [ ! -f "${cfg}" ]; then
  echo "config.xml not found at ${cfg} — mirror the skynet-opnsense repo first (A2 row 6)" >&2
  exit 0
fi

# Parse with Python stdlib (no external deps — no xmllint needed).
python3 - "${cfg}" "${outdir}" <<'PY'
import sys, json, datetime
import xml.etree.ElementTree as ET

cfg, outdir = sys.argv[1], sys.argv[2]
root = ET.parse(cfg).getroot()

# Defense in depth: config.xml carries hashed secrets. This inventory is committed to git,
# so NEVER copy a value from a sensitive-looking child tag — drop the key entirely, whether
# or not it currently has a value. (A blank today can be populated tomorrow.)
SENSITIVE = ("password", "passwordagain", "secret", "sharedsecret", "shared_secret",
             "pre_shared_key", "psk", "privatekey", "private_key", "passphrase",
             "apikey", "api_key", "token", "md5password", "cryptokey", "key", "hash")

def _sensitive(tag):
    t = tag.lower()
    return any(s in t for s in SENSITIVE)

def rows(el):
    return [{c.tag: (c.text or "") for c in e if not _sensitive(c.tag)}
            for e in el] if el is not None else []

def find_all(path):
    return rows(root.findall(path))

# Aliases (modern plugin path, legacy fallback).
aliases = find_all("./OPNsense/Firewall/Alias/aliases/alias") or find_all("./aliases/alias")

# Rules: merge legacy (./filter/rule) + modern plugin (./OPNsense/Firewall/Filter/rules/rule).
rules = find_all("./filter/rule") + find_all("./OPNsense/Firewall/Filter/rules/rule")

# DHCP reservations: best-effort across Kea, ISC dhcpd, and dnsmasq host entries.
reservations = []
for p in (".//OPNsense/Kea/dhcp4/reservations/reservation",
          "./dhcpd/lan/staticmap",
          "./dnsmasq/hosts"):
    reservations += find_all(p)

data = {
    "collected": datetime.datetime.now().astimezone().isoformat(),
    "source": cfg,
    "counts": {"aliases": len(aliases), "rules": len(rules), "reservations": len(reservations)},
    "aliases": aliases,
    "rules": rules,
    "reservations": reservations,
}
with open(f"{outdir}/firewall.json", "w") as f:
    json.dump(data, f, indent=2)
print(f"wrote {outdir}/firewall.json  "
      f"(aliases={len(aliases)}, rules={len(rules)}, reservations={len(reservations)})")
PY
