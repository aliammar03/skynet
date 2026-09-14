---
date: 2026-09-15
time: 00:24:58            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P11 deployment orchestration implementation
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, vm-docker-dmz, librespeed]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-15 · session · SKY-025 P11 deployment orchestration implementation

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started SKY-025 P11 from `main` after confirming PR #257 was merged. Created
`phase/sky-025-p11-deploy` while 33 pre-existing generated/inventory/drift entries were dirty and left
those entries outside P11 ownership. Heavy construction used Companion and Investigator reads, one
Senior Executor for the packaged write/recovery code, an independent Tester, and an Archivist for
current docs and stable memory.

The first approved live command was `PYTHONPATH=src python -m skynet deploy service librespeed --repo
/home/aliammar/skynet --branch main --no-deploy --json`. It stopped before a write because the new
Arcane writer initially required HTTPS while the installed internal endpoint is HTTP. The executor
removed that incompatible restriction without widening the credential parser or redirect policy.

The repeated source and Nix-package live commands reached Arcane with source revision
`f8072b390c10957a572eda4aa112da0583e46796`. Arcane's pull returned an HTTP failure. The subsequent
read-only sync observation recorded `lastSyncStatus=failed` and the safe error classification
`authentication required: Invalid username or token`. The packaged outcome was `status=failed`,
`verification=failed-closed`, completed only `repository-selected` and `sync-selected`, and reported
`source pull unresolved; inspect its commit/status before retry`. No environment replacement or
runtime action ran.

## Actions & outcomes
- Migrated Arcane sync, environment, deploy, runtime, and rollback preparation into
  `src/skynet/gitops.py`; the two legacy shell commands became thin forwarders.
- Replaced shell-sourced credentials and local plaintext temp env files with literal credential
  parsing and an in-memory sops result streamed only through SSH stdin to an atomic remote file.
- Independent disposable verification found five defects: inherited-pipe timeout hang, mixed-project
  rollback acceptance, an uncaught degenerate changed path, implicit acceptance of missing sync
  controls, and loss of env-write ambiguity after malformed owner output. The executor repaired each;
  the same Tester reran the reproductions and returned PASS.
- A report-only rollback smoke against real commit `bbf5c053fbbe415b272e6162112db9c81d5df728`
  initially exposed that strict single-directory validation rejected its paired
  `compose/caddy-apps/Caddyfile` publication change. The final validator allows that explicit
  publication pair, reports the complete inverse path set, and rejects other Compose projects and
  protected gate/constitutional paths.
- Ruff, strict mypy, compileall, shell syntax, offline Nix build, hard invariants, secret scan, and
  diff checks passed without adding an automated test suite.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- HTTPS-only Arcane writes → abandoned because the current internal Arcane endpoint is configured
  as HTTP and P11 cannot silently disable the existing T2 actuator.
- Require every rollback commit path to live under `compose/<service>/` → abandoned because real
  service publication commits also change the reviewed apps-Caddy route and would become impossible
  to recover through the declared whole-commit revert path.

## Follow-ups / open threads
- Repair Arcane's registered GitHub repository credential through its authorized administrative
  boundary, then rerun a successful P11 live deploy/env/runtime/gate smoke. Do not place the token or
  credential contents in journal, chat, or command output.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
