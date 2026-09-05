---
date: 2026-09-06
time: 02:04:41            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-023 Phase 10 T1 classifier and base build checkpoint
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-06 · session · SKY-023 Phase 10 T1 classifier and base build checkpoint

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Added scripts/repo-surface.sh as the shared tracked-text classifier. Temporal hygiene,
documentation drift, and bin/ops hygiene now consume its current-authority output. Planning,
journal/history/ADR, generated, test/fixture, and opaque content have explicit classes; other
tracked text defaults to current.

Removed temporal provenance from newly covered current surfaces, reduced CLAUDE.md to an import
shim, and renamed the generic flake LXC build target to lxc-base. `nix build .#lxc-base-tarball
--no-link` completed with `/nix/store/acq10jfpp70dqyf3yd9h8irb807wjvb9-tarball`. No Proxmox API
call, template upload, Tofu change, root grant, credential handling, or live infrastructure action
occurred.

## Actions & outcomes
- `bin/ops hygiene` → temporal and documentation-drift gates passed; current authority was 166,437
  approximate tokens, below the configured 170,000-token limit.
- `./.githooks/pre-commit` and `nix flake check --no-write-lock-file` → passed locally.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- The first lxc-base build failed because Nix cannot read an untracked new host directory from the
  flake source. Added `hosts/lxc-base/default.nix` with intent-to-add and reran successfully.

## Follow-ups / open threads
- T2 checkpoint remains: upload the verified lxc-base template to Proxmox, verify storage visibility,
  change new-create Tofu references, inspect a saved no-op plan for existing CTs, and only then retire
  the old template through reviewed cleanup.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
