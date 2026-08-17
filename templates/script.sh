#!/usr/bin/env bash
# __NAME__ — <one line: what it does → what it produces>.
# TIER: T1|T2|T2+|T3 — the blast radius; the reader must know it before running.
# USAGE: scripts/__NAME__.sh <args>
#   <if it reads creds: from /opt/skynet-ops/secrets/<name>.env — reference by var, never echo a value>
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Guard required args so a bare call self-documents. — docs/conventions/scripts.md
arg="${1:?usage: __NAME__.sh <args>}"

# … do the work here.
# Conventions this skeleton bakes in (scripts.md):
#   • idempotent where possible — re-running converges, never duplicates;
#   • a read-only collector NEVER mutates remote state (that makes it T1 by contract);
#   • never print a secret to stdout/logs/transcripts;
#   • for internal APIs (Proxmox/PBS/Technitium), pin the cert — never `curl -k`:
#       curl --cacert "${SOME_CACERT}" "https://host:port/…"
echo "TODO: implement __NAME__ (${arg})"
