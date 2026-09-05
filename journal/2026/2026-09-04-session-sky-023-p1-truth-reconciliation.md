---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-023 P1 truth reconciliation
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023, SKY-003, SKY-018, SKY-020, SKY-021, SKY-024, ADR 0006]
---

# 2026-09-04 · session · SKY-023 P1 truth reconciliation

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened

Read `docs/generated/06-agent-digest.md`, `07-context-map.md`, `planning/README.md`, and the SKY-023
idea. The worktree was clean on `main` at `5000d61`. Created branch `phase/sky-023-p1`, ran
`bin/plan start SKY-023`, and read the promoted project in full. No infrastructure write, credential,
or root grant was used; current runtime evidence came from executable code, tests, and inventory
collected earlier on 2026-09-04.

Delegated two read-only audits. One traced OpenTofu/trust/grant/drift claims; the other traced
Arcane/Omada/forward-auth/L5 claims. Both returned file-and-line conflict matrices and changed no
files. Their evidence was folded into `/tmp/sky-023-p1-conflict-matrix.md`, deliberately outside git;
Phase 4 owns its eventual archive.

The OpenTofu audit found a claim beyond the original list: `scripts/tofu-apply.sh` includes guest
`create` and `update` actions in its pre-snapshot set. A planned new VMID cannot answer the snapshot
API call, so the wrapper exits 4 before applying. `tests/tofu-rollback-test.sh` stubs snapshot success
and has no real new-guest case. Because SKY-023 requires all production writes through the wrapper,
the VM/LXC runbooks now stop before apply rather than documenting a bypass.

## Actions & outcomes

- `scripts/gitops-deploy.sh` inspection + current missing-`project.env` evidence → selected the
  repo-driven GitOps truth: `.env.git` + decrypted `.env.sops` materialized to `0600 .env` by the
  wrapper; `project.env` is legacy import only.
- SKY-020 frontmatter/plan + absence of OPNsense provider/resources → recorded T1 read as live,
  non-leash config as constitutionally approved T2 but not implemented, and privileged/self-leash
  operations as T3.
- Core/network ACL inventory + `invariants.json` → recorded 5001/635/837 as network-envelope
  unreachable and Unraid 2020 as unpooled/never-destroyed but core-envelope config/power reachable;
  Unraid guest-OS root remains T3.
- `inventory/network-gear.json` + firewall inventory → moved Omada reachability from planned to
  realized T1 read; administration remains T3.
- live Caddy/cloudflared config + `inventory/routes.json` → recorded Authentik forward-auth as
  proven for calibre; additional apps are routine extension.
- A5.5 history + DR runbook → narrowed the L5 claim: Drive-to-scratch-PBS archive reconstruction
  is proven (184/184 chunks, byte-identical `root.pxar`); full core-loss rebuild/attach/boot is not.
- `bin/grant-root` + cert loader → replaced legacy single-cert instructions with canonical
  `~/.ssh/certs/<host>-cert.pub`; concurrent grants are supported.
- `scripts/nightly.sh` + deploy rollback tests → corrected nightly drift to report-only; automatic
  git revert exists only for an explicitly gated deploy.
- Replaced every production runbook's bare/re-planning OpenTofu apply with merged-source → saved
  plan → exact-plan review → explicit approval → `scripts/tofu-apply.sh`.
- `scripts/check-invariants.sh` → all hard-law checks passed.
- All nine `tests/*-test.sh` files → 139 assertions passed, 0 failed.
- `bash -n` over every edited shell executable → passed.
- Relative-link/command-reference check over 28 changed Markdown files → passed after correcting
  eight stale `planning/projects/` links to archived directives; 46 local command references exist.

## Graveyard — tried & abandoned

- Running the relative-link checker with Ruby → abandoned because `ruby` is not installed; the
  same read-only check was rerun with Perl.
- Sending new-guest plans directly to `tofu-apply.sh` → abandoned because the wrapper must snapshot
  before apply and a new VMID has no snapshot target. Skipping snapshots or auto-deleting a partial
  create would weaken the rollback/destruction laws.
- Treating OPNsense config T2 as already live → abandoned after SKY-020 showed only Phase 1/T1 read
  is complete and `tofu/` contains no OPNsense provider/resources.

## Follow-ups / open threads

- Phase 1 was paused before close-out. A delegated final review found six remaining corrections:
  DNS deletion rollback must not claim `tofu-apply.sh` can apply deletes; non-guest OpenTofu writes
  have no automatic snapshot rollback; the OPNsense write actuator is pending SKY-020; nightly route
  collection does not compare live Caddy config with git; Obsidian is the own-auth reference while
  calibre is the proven forward-auth reference; and the forward-auth runbook must put the merged PR
  before Authentik API mutations.
- Resume Phase 1 on `phase/sky-023-p1`. Apply those corrections, including the related comments in
  `scripts/gitops-deploy.sh`, `tofu/cloudflare-dns.tf`, and `tofu/pool-cts.tf`; clarify that the core
  credential can technically reach Unraid 2020's envelope although policy forbids destructive use.
- Re-run owning generators sequentially, then the full invariant/test/syntax/link suite and
  `git diff --check`. Only then mark Phase 1 complete and open its human-merged PR.
- Phase 2 remains out of scope until the Phase 1 PR is reviewed and merged.
- Design and failure-test a compliant new-guest create executor before VM/LXC provisioning is used
  again; the production runbooks now fail closed at that boundary.
- Design a rollback path for non-guest OpenTofu writes and a detector that compares live Caddy
  configuration with git; neither capability is A4-eligible today.
- `envsync.sh` should return cleanly when current GitOps projects lack legacy `project.env`; the
  2026-09-04 nightly reported exit 1 even though absence is now classified as expected.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
