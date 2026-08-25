---
date: 2026-08-26
kind: session
title: nightly 2026-08-26 (deterministic)
tier_touched: [T1]
grants: []
refs: [runbooks/nightly.md, "inventory/2026-08-26"]
---

# 2026-08-26 · session · nightly (deterministic path)

Report-only nightly ran the deterministic fallback (no LLM this run): `bin/ops collect`
(T1 read-only), `envsync`, `render-docs`. Raw — no narrative, no `05-state-of-the-lab.md`,
no grant audit (those need the agent path).

## What changed (staged this run)

```
 docs/generated/00-network-map.md                  |   6 +-
 docs/generated/06-agent-digest.md                 |  20 +-
 docs/generated/07-context-map.md                  |  22 +-
 docs/generated/10-vlans.md                        |   7 +-
 docs/generated/20-firewall.md                     |  18 +-
 docs/generated/30-services/README.md              |   4 +-
 docs/generated/40-hosts/server-proxmox-core.md    |   5 +-
 docs/generated/40-hosts/server-proxmox-network.md |   6 +-
 docs/generated/90-backup-status.md                |   4 +-
 docs/generated/README.md                          |   4 +-
 inventory/dns-zones.json                          | 126 +++----
 inventory/firewall/firewall.json                  |  48 ++-
 inventory/proxmox-core.json                       | 404 ++++++++++++----------
 inventory/proxmox-network.json                    | 392 ++++++++++-----------
 14 files changed, 566 insertions(+), 500 deletions(-)
```

## Graveyard — tried & abandoned

— nothing abandoned (a clean deterministic pass) —

## Follow-ups / open threads

- Agent-path nightly would add the narrative + grant audit this raw entry omits.
