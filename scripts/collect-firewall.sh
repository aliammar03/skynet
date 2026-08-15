#!/usr/bin/env bash
# collect-firewall.sh — parse the mirrored OPNsense config.xml → inventory/firewall/*.json
# USAGE: collect-firewall.sh [path-to-config.xml]
#   Truth source is the skynet-opnsense-backup repo (os-git-backup auto-pushes config.xml).
#   NO management-plane access — we read the git mirror, never OPNsense itself (T3).
#   Default clone location: /opt/skynet-ops/mirror/skynet-opnsense-backup/config.xml
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cfg="${1:-/opt/skynet-ops/mirror/skynet-opnsense-backup/config.xml}"
outdir="${REPO_DIR}/inventory/firewall"
mkdir -p "${outdir}"

if [ ! -f "${cfg}" ]; then
  echo "config.xml not found at ${cfg} — collector idle until the backup repo is mirrored (A2 row 6)" >&2
  exit 0
fi

command -v xmllint >/dev/null || { echo "xmllint (libxml2-utils) required to parse config.xml" >&2; exit 1; }

# Convert XML → JSON via python stdlib (no extra deps).
python3 - "${cfg}" "${outdir}" <<'PY'
import sys, json, datetime
import xml.etree.ElementTree as ET

cfg, outdir = sys.argv[1], sys.argv[2]
root = ET.parse(cfg).getroot()

def collect(path):
    return [{c.tag: (c.text or "") for c in el} for el in root.findall(path)]

data = {
    "collected": datetime.datetime.now().astimezone().isoformat(),
    "aliases": collect("./OPNsense/Firewall/Alias/aliases/alias") or collect("./aliases/alias"),
    "rules": collect("./filter/rule"),
    "dhcp_static": collect("./dhcpd/lan/staticmap"),
}
with open(f"{outdir}/firewall.json", "w") as f:
    json.dump(data, f, indent=2)
print(f"wrote {outdir}/firewall.json  "
      f"(aliases={len(data['aliases'])}, rules={len(data['rules'])})")
PY
