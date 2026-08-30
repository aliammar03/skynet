---
date: 2026-08-30
kind: session          # session | incident | decision
title: nightly 2026-08-30 second pass
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [runbooks/nightly.md, "inventory/2026-08-30", "PR #113", "PR #115", "PR #116", SKY-008]
---

# 2026-08-30 · session · nightly 2026-08-30 second pass

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Second agent-path nightly of 2026-08-30 (Claude, manual invocation) per `runbooks/nightly.md`.
The earlier pass this morning produced PR #116; since then #113 (nightly 08-28), #115 (nightly
08-29) and #116 (nightly 08-30) all landed on `main` in quick succession — `git log` shows
991fa58 (#116) committed 2026-08-30 13:02:09 +0500, bf44910 (#115) 13:01:17, 3844655 (#113)
12:59:54. So the nightly-PR merge backlog flagged in the last two narratives is now **cleared**:
local `main` == `origin/main` == 991fa58, clean working tree at start.

`git fetch origin --prune` dropped the merged `inventory/2026-08-{28,29,30}` remote branches and
picked up one new unrelated branch `claude/netbox-vs-nautobot-apdxof`. No new commits on
`origin/main` beyond 991fa58.

Ran on `main`, then branched `inventory/2026-08-30` off 991fa58 for the PR.

`bin/ops collect` ran clean: proxmox-core, proxmox-network, docker-docker-dmz, dns-zones,
firewall all wrote; render-docs ran inline. PBS collector stayed idle (no creds at
`/opt/skynet-ops/secrets/pbs.env`, expected — A2/A4 gate). `scripts/envsync.sh`: "no env changes"
across all 10 known projects (none has a `project.env` on host). Explicit re-runs of
`render-docs.sh`, `render-digest.sh`, `render-context-map.sh` all wrote clean.
`06-agent-digest.md` and `07-context-map.md` came out byte-identical to `main` (no ADR / journal
/ roadmap source change since #116) — `git status` shows them unmodified.

No active root grant: `~/.ssh/certs/` absent, `/opt/skynet-ops/grants/` absent, no
`inventory/grant-audit.json`. Skipped runbook step 5 (grant audit).

Diffed the five inventory JSONs against `git show HEAD:...` (== `main` == #116's output). Because
`main` has caught up, "diff vs main" and "diff vs last night" are the same question again for the
first time in ~4 nights.

## Actions & outcomes
- `git fetch origin --prune` → merged nightly branches deleted locally; `origin/main` unchanged at 991fa58.
- `git checkout -b inventory/2026-08-30` off 991fa58.
- `bin/ops collect` → refreshed all 5 inventory files, ran `render-docs.sh` inline.
- `./scripts/envsync.sh` → "no env changes".
- `./scripts/render-docs.sh` / `render-digest.sh` / `render-context-map.sh` (explicit) → all clean;
  digest + context-map byte-identical to `main`, only the `docs/generated/*` factual pages moved
  (frontmatter `generated:` timestamp 2026-08-30T13:01:31 → 13:05:32 only — no content change).
- Diff vs `main` (== #116) found only churn:
  - **Proxmox core + network**: no guest add/remove, no state change. Confirmed by diffing
    `resources[] | select(.type=="qemu" or "lxc") | vmid,type,status,name,pool,template` sorted —
    identical both nodes. Remaining JSON diff is unstable key ordering + live metric fields
    (cpu/mem/disk/uptime/netin/netout) — known collector noise, harmless.
  - **PBS CT 240 on the core node** (`lxc-proxmox-backup-server`, pool `ops-managed`): still
    `stopped`. Unchanged since #116; last seen `running` 2026-08-27. NOTE: the *network*-node
    CT 240 (same name `lxc-proxmox-backup-server`, no pool) is `running` — the stopped one is
    specifically the `ops-managed` core instance. Still unexplained, still not acted on (T2
    guest-power, out of report-only scope).
  - **VMID 999** (legacy pre-NixOS `vm-skynet-ops`, no pool): still `running`. Unchanged.
  - **9091** (`vm-skynet-ops-nix`) `stopped`, **9000** (`ubuntu-2404-base`) `stopped` template,
    **9090** (`vm-skynet-ops`) `running` — all as expected.
  - **docker-docker-dmz**: 18 containers, all `running`, no add/remove, no image change, no state
    change. Only `Status`/`RunningFor`/`Size`/`CreatedAt` string churn.
  - **dns-zones**: secondary zone `soaSerial` 2026082901 → 2026083000 (routine AXFR refresh);
    `lastModified` / `expiry` advanced; three record `lastUsedOn` timestamps moved, including the
    `10.10.100.35` A-record (`lastUsedOn` 2026-08-28T21:19 → 2026-08-30T07:50 — still being
    queried despite CT 1035 / caddy-dmz being `stopped`; a client querying the name, not proof the
    host answers). No record adds/removes/edits.
  - **firewall.json**: content byte-identical — 41 aliases, 29 rules, 6 reservations; mirror HEAD
    still `aba7911` (2026-08-26 15:10 +0500). Only the collector timestamp moved.
- Rewrote `docs/generated/05-state-of-the-lab.md` — dated 2026-08-30, framed as "backlog cleared,
  byte-quiet since #116"; PBS-core-stopped and VMID-999-running carried forward as the two
  standing watch items.
- `bin/new journal session "nightly 2026-08-30 second pass"` → this entry (plain
  `"nightly 2026-08-30"` collides with the morning pass's file; `bin/new` refuses same-slug —
  episodes are append-only, so used a distinct title).

## Graveyard — tried & abandoned
- `bin/new journal session "nightly 2026-08-30"` → refused: `journal/2026/2026-08-30-session-nightly-2026-08-30.md`
  already exists (this morning's pass). Retried with title `"nightly 2026-08-30 second pass"`.
- No other dead ends — with `main` caught up there was no need for the `f9d63d9`-relative
  side-diff the last two passes used to see around a stale `main`.

## Follow-ups / open threads
- **PBS CT 240 (core, `ops-managed`) — still stopped**, last running 2026-08-27. No change since
  #116. The network-node PBS is up, so this is not a total backup outage, but the L5
  PBS-datastore→Drive mirror for the core instance has had nothing fresh to mirror for days.
  Still needs a human call: deliberate maintenance vs unplanned stop.
- **Nightly-PR backlog: CLEARED.** #113 / #115 / #116 all on `main`; `main` now tracks reality.
- **VMID 999 still running, unexplained** — carried forward, not worsening.
- From the 2026-08-28 entity-model decision (via the agent digest, not re-verified tonight):
  `10.10.100.35` ownership must be resolved before CT 1035 (caddy-dmz, stopped) is destroyed —
  nine published apps depend on it; the record is still being queried (see dns diff above). CT 526
  (UniFi controller, network node) running and unmapped in DNS/reservations. `arcane-manager`
  GitOps-exception status still Ali's call.
- **SKY-008 P3** (DNS provider + declarative LXC import) still not started — Phase 1+2 done both
  nodes.
