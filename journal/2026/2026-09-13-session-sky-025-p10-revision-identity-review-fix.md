---
date: 2026-09-13
time: 17:25:00            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P10 revision identity review fix
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #257, vm-skynet-ops, vm-docker-dmz] # SKY-###, PR #NNN, ADR NNNN, hosts
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P10 revision identity review fix

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
The fresh review of PR #257 found that `scripts/gitops-deploy.sh --gate` still computed its second
argument with `git log -1 --format=%H -- compose/${SVC}/`, while the new `deploy-gate.sh` interpreted
that argument as the exact live Git Sync revision. On the reviewed base, local/main and live Arcane
were `c800d58cd4dc8e97cfe219b8ee14c4bb5cd7fa40`; the newest commit touching
`compose/caddy-apps` was `44ae7d374e01512ac85e997494952546eda9da5e`. A healthy Caddy deployment could therefore fail with
`GitOps sync revision mismatch`.

## Actions & outcomes
- Removed `--revert-commit` from `gitops-deploy.sh` → the report-only P10 path no longer accepts or
  carries rollback-candidate identity.
- Validated `GITOPS_BRANCH` before credentials or Arcane use and, only for `--gate`, resolved the exact
  local `refs/heads/<branch>` commit → the thin forwarder receives one unambiguous expected live SHA.
- Ran an independent disposable full caller-chain harness with branch head `c800d58` and service-touch
  commit `44ae7d3` → `gitops-deploy.sh --gate` forwarded `c800d58`; the legacy option exited 2; invalid
  branches failed before credential/T2 use; no rollback or real deployment command ran.
- Ran source live smokes for routed `aiometadata` and unrouted `caddy-apps` and Nix-installed live
  smokes for routed `calibre` and unrouted `cloudflared` → all succeeded at `c800d58`, routed TLS result
  0. A source run expecting `250bb48` exited 1 with `GitOps sync revision mismatch`.
- Re-ran Ruff, strict mypy, Python compile, Bash syntax, offline Nix build, diff checks, secret scan, and
  hard invariants through the independent Tester → all passed.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Reusing the newest commit touching `compose/<service>` as live identity → abandoned because it is a
  service-history/rollback concept and can differ from the Git Sync branch head.
- Retaining `--revert-commit` on a report-only verifier caller → abandoned because P10 has no rollback
  action and P11 owns recovery identity/preparation.

## Follow-ups / open threads
- Publish the repair to PR #257, then start a new fresh external review. Do not reuse the prior verdict.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
