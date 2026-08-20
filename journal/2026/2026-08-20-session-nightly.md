---
date: 2026-08-20
kind: session
title: nightly 2026-08-20 (deterministic)
tier_touched: [T1]
grants: []
refs: [runbooks/nightly.md, "inventory/2026-08-20"]
---

# 2026-08-20 · session · nightly (deterministic path)

Report-only nightly ran the deterministic fallback (no LLM this run): `bin/ops collect`
(T1 read-only), `envsync`, `render-docs`. Raw — no narrative, no `05-state-of-the-lab.md`,
no grant audit (those need the agent path).

## What changed (staged this run)

```
 docs/generated/00-network-map.md                  |   4 +-
 docs/generated/06-agent-digest.md                 |  30 +-
 docs/generated/07-context-map.md                  |  27 +-
 docs/generated/10-vlans.md                        |   4 +-
 docs/generated/20-firewall.md                     |   4 +-
 docs/generated/30-services/README.md              |   4 +-
 docs/generated/40-hosts/server-proxmox-core.md    |   6 +-
 docs/generated/40-hosts/server-proxmox-network.md |   8 +-
 docs/generated/90-backup-status.md                |   4 +-
 docs/generated/README.md                          |   4 +-
 inventory/dns-zones.json                          |  38 +-
 inventory/firewall/firewall.json                  |   2 +-
 inventory/proxmox-core.json                       | 384 ++++++++++-----------
 inventory/proxmox-network.json                    | 400 +++++++++++-----------
 14 files changed, 462 insertions(+), 457 deletions(-)
```

## Graveyard — tried & abandoned

— nothing abandoned (a clean deterministic pass) —

## Follow-ups / open threads

- Agent-path nightly would add the narrative + grant audit this raw entry omits.
