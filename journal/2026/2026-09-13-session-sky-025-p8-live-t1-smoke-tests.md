---
date: 2026-09-13
time: 10:06:31            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P8 live T1 smoke tests
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #255"] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P8 live T1 smoke tests

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
The first `collect-status` against `/home/aliammar/skynet` returned `outcome=unavailable` because the
retained inventory did not have a complete current receipt set. Ali then explicitly authorized a T1
`collect all`.

Created detached temporary worktree `/tmp/skynet-p8-smoke.0k6Te3` at PR #255 head `8184cf7` and ran
the packaged `collect all` with the standing default read-only credential files. Credential contents
were not printed or copied. Collection contacted the declared Proxmox, PBS, Docker, Technitium,
OPNsense, Omada, certificate, and static-route read paths and wrote only the temporary worktree.

After the smoke checks, `git worktree remove --force /tmp/skynet-p8-smoke.0k6Te3` removed the collected
temporary inventory/cache/generated docs. The three temporary log files under `/tmp` were unlinked.

## Actions & outcomes
- `./bin/skynet collect all --repo /tmp/skynet-p8-smoke.0k6Te3 --json` → success for all 11
  collectors: 8 core guests, 6 network guests, 18/2 ACL paths, 1 PBS datastore with 189 snapshots,
  18 Docker containers/31 images, 4 DNS zones/13,356 records, 40 firewall aliases/28 rules, 44 ARP
  entries/17 interfaces, 3 Omada devices, 7/7 reachable certificate probes, and 9 routes.
- `collect-status` against that worktree → success with receipts from 05:04:57–05:05:06 UTC.
- Packaged entity audit → success: 14 guests, 11 services, 2 nodes, 9 vhosts, 3 network devices;
  zero holes; guest buckets were 8 matched, 4 exception, 1 template, 1 stale.
- Freshness-gated `bin/ops query` → 14 guests, 12 running guests, 11 containers, all 11 containers
  entity-hosted, 9 routes, and 19 front-door DNS rows.
- `bash scripts/render-docs.sh` in the temporary worktree → success; both maintained SQL-backed views
  and host pages rendered.
- Deliberately invalid query `SELECT * FROM smoke_missing_table` → exit 1 with `cache: query failed`.

## Graveyard — tried & abandoned
- Reusing the original checkout's retained inventory as fresh evidence → abandoned after
  `collect-status` failed closed; the live pass used an isolated worktree instead.

## Follow-ups / open threads
- Fresh external review of PR #255 remains the next step; this smoke run is implementation evidence,
  not external acceptance.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
