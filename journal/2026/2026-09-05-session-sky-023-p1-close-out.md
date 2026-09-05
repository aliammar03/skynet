---
date: 2026-09-05
kind: session          # session | incident | decision
title: SKY-023 P1 close-out
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023, SKY-020, ADR 0005, ADR 0006]
---

# 2026-09-05 · session · SKY-023 P1 close-out

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened

Resumed `phase/sky-023-p1` at checkpoint commit `7ae5404`. Read the promoted directive and its
linked 2026-09-04 truth-reconciliation episode. No infrastructure host, credential, T2 write, or
root grant was used. One new read-only Scout independently re-checked the six recorded delegated
review blockers and returned file-and-line evidence; the lead verified the cited code and inventory.

## Actions & outcomes

- `scripts/tofu-apply.sh` and `tests/tofu-rollback-test.sh` → made the executor's real boundary
  explicit: existing guests get automatic snapshot rollback; non-guest resources get saved-plan,
  delete, and verification guards but no automatic inverse. The added stub failure case took no
  snapshot and emitted `non-guest changes need operator recovery`.
- `docs/design/actuators.md` → split existing-guest and non-guest OpenTofu rows; marked the OPNsense
  write actuator pending SKY-020 instead of live/tested; removed the false tofu-delete rollback.
- `runbooks/publish-service.md` + identity/proxy docs → put Caddyfile PR merge before Authentik API
  mutation, kept policy changes T3, named Obsidian/CouchDB as the proved own-auth reference and
  calibre as the live forward-auth reference, and made DNS removal a separate hard checkpoint that
  never enters the delete-refusing wrapper.
- `scripts/collect-routes.sh` inspection → confirmed it parses only the committed Caddyfile. Updated
  the design and `scripts/gitops-deploy.sh` comment so nightly route inventory no longer claims a
  live-Caddy-versus-git comparison.
- `docs/design/access-and-trust.md` → stated that core's root-ACL operate credential can technically
  change/power Unraid VM 2020's envelope while policy keeps it unpooled and forbids destructive use;
  guest-OS root remains T3.
- `tofu/cloudflare-dns.tf`, `tofu/pool-cts.tf`, and `scripts/cf-dns-route.sh` comments → replaced bare
  or misleading apply/rollback shorthand with the current saved-plan/create-blocked/delete-checkpoint
  behavior.
- Ran `render-docs.sh`, `render-digest.sh`, and `render-context-map.sh` sequentially → owned generated
  views refreshed from current sources and inventory.
- `scripts/check-invariants.sh` → all six machine-checkable law groups passed.
- All nine `tests/*-test.sh` files → 140 assertions passed, 0 failed.
- `bash -n` over every Phase 1-edited executable and the updated test → passed.
- Relative-link validation over 40 changed Markdown files + local command-reference validation →
  passed; `git diff --check` passed.
- Literal scan of `runbooks/` for bare `tofu apply` → zero matches.

## Graveyard — tried & abandoned

- A diagnostic `rg` command embedded the search phrase in shell backticks. The shell invoked
  `tofu apply` twice from the repository root; OpenTofu returned `No configuration files` both times
  before planning or mutation. Re-ran the scans with fixed-string/single-quoted patterns. No state or
  infrastructure changed.
- Applying a source-removal plan through `scripts/tofu-apply.sh` → rejected because the wrapper
  deliberately refuses every delete/replace. Public Cloudflare removal stays an explicit
  `cf-dns-route.sh --delete` checkpoint; current Technitium deletion remains blocked by token scope.

## Follow-ups / open threads

- Human-review and merge the Phase 1 PR; the agent does not merge authored work.
- Phase 2 may start only after Phase 1 merges. It owns constitution/spoke pruning and size targets;
  no Phase 2 pruning was performed here.
- SKY-020 still owns the OPNsense provider, write credential, policy gate, apply, and rollback proof.
- Design failure-tested rollback executors for non-guest tofu writes and new-guest creates before
  either capability can reach A4; add live-Caddy-versus-git drift detection separately.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
