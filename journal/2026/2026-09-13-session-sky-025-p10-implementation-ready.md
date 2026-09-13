---
date: 2026-09-13
time: 16:50:34            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P10 implementation ready
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #257, vm-skynet-ops, vm-docker-dmz] # SKY-###, PR #NNN, ADR NNNN, hosts
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P10 implementation ready

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started SKY-025 P10 from merged P9 commit `c800d58` on the Heavy route. The checkout already contained
33 modified/untracked collector, generated-page, and drift artifacts; the P10 branch left them outside
its commits. Read `/opt/skynet-ops/secrets/arcane.env` through the new literal-assignment path and made
read-only Arcane requests. Used Docker context `docker-dmz` for project observations and bounded ingress
probes. No root grant was issued.

The first live API read showed all ten Git Sync records at `250bb48` while `main` was `c800d58`; at
16:26 PKT Arcane synced and all records moved to `c800d58`. The first full verifier run then failed five
healthy services with `malformed Docker container observation`. Raw Docker `.Labels` strings contained
commas inside `com.docker.compose.depends_on` and OCI description/build labels; parsing the entire string
as comma-separated key/value pairs was wrong.

Independent disposable verification returned three repair rounds. The first found permissive route
counts/fields/hostname parsing, an uncaught non-string environment ID, and shell argc exit 1. The second
found duplicate vhost rows and missing canonical alias/auth checks. The third found case-variant DNS
duplicates. Each defect returned to the same Executor and the same Tester rechecked it.

## Actions & outcomes
- Added `src/skynet/deployment.py` and `skynet verify deployment` → exact sync/project revision,
  positive complete Arcane counts, non-empty matching Docker containers, all-running/all-healthy state,
  canonical routes, DMZ-vantage HTTPS, and valid TLS are required for success.
- Replaced `scripts/deploy-gate.sh` logic with a package forwarder → no duplicate health implementation,
  `eval`, automatic rollback call, or shell-owned verdict remains.
- Ran the repaired source verifier across ten projects → 10 success; 18 containers matched Arcane
  counts and were running/healthy; eight routed services returned 200/302/307/401 with TLS result 0;
  `caddy-apps` and `cloudflared` returned success with route status `skipped`.
- Ran the verifier with stale revision `250bb48` after Arcane reached `c800d58` → exit 1 with
  `GitOps sync revision mismatch`.
- Built `.#skynet` through Nix and ran its installed CLI for routed `calibre` and unrouted
  `caddy-apps` → both success; calibre returned HTTP 302 and TLS result 0.
- Ran Ruff, strict mypy, compile, Bash syntax, Nix build, secret scan, hard invariants, and diff checks
  → all passed under the automated-test/CI embargo.
- Opened draft PR #257 from `phase/sky-025-p10-verification` → substantive implementation is published;
  pre-review documentation and handoff remain to be sealed.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Apps-Caddy BusyBox `wget` as the ingress probe → abandoned because some names did not resolve there,
  and its build printed `TLS certificate validation not implemented` when forced through `/etc/hosts`.
- Splitting Docker's flattened `.Labels` string on commas → abandoned because legitimate label values
  contain commas and five healthy projects false-failed.
- Deduplicating route vhosts before probing → abandoned because contradictory and case-variant DNS rows
  are ambiguous evidence that must fail closed.

## Follow-ups / open threads
- Fresh external review of PR #257 is required. Accepted progress remains P9/24 until an ACCEPT marker
  is validated and bounded closeout is staged on the same PR.
- P11 owns deployment source identity, polling/retry, env/sync execution, and rollback preparation.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
