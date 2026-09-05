---
date: 2026-09-06
time: 01:02:24            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-023 Phase 6 code and config hygiene close-out
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-06 · session · SKY-023 Phase 6 code and config hygiene close-out

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Verified that Phase 5 had merged as `f3806a4`, fast-forwarded local `main`, and created
`docs/sky-023-p6-code-hygiene`. This was T1 repository work only: no infrastructure command,
credential access, T2 write, or root grant ran.

Read the scripts convention and scanned live scripts, entry points, OpenTofu, Nix, host definitions,
sops rules, compose/config files, and flake metadata. Removed numeric directive and phase provenance,
pilot/rehearsal narration, and historical replacement stories from comments and user-visible runtime
strings. The sweep changed generated snapshot descriptions to `pre-tofu-apply safety snapshot` and
the saved-plan executor's snapshot prefix to `pre-tofu-apply-<timestamp>`.

Retained load-bearing current constraints: provider import ignores and `moved` blocks, the per-CT
recipient rules, saved-plan scope and rollback guards, the live collector's DR/offline counterpart,
and the generic `SKY-000` placeholders in `bin/plan` that stamp directive templates.

## Actions & outcomes
- `rg` scan across live code/config comments and runtime strings → no `SKY-[0-9]{3}` provenance
  remained outside `bin/plan`'s generic template substitution.
- Archaeology-pattern scan (`used to`, `previously`, `retired`, `replaced`, `piloted`, and related
  terms) → no current-authority narration remained.
- `bash .githooks/pre-commit` → all deterministic checks passed.
- `nix flake check --no-write-lock-file` → evaluated all NixOS configurations and the LXC tarball;
  Nix emitted only its existing `system` rename warning and `deploy` output warning.
- `git diff --check` → no whitespace errors.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Removing `bin/plan`'s `SKY-000` substitutions → abandoned because they are generic directive
  template mechanics, not provenance in an operational artifact.
- Removing OpenTofu import compatibility comments or `moved` blocks → abandoned because they
  describe current provider/state constraints and protect live guests from drift or recreation.

## Follow-ups / open threads
- Continue SKY-023 at Phase 7; read [[SKY-023-progress]], verify reality, and execute only that phase.
- Phase 7 owns behavior-level adjudication of retained migration and compatibility helpers,
  including `scripts/envsync.sh`, `scripts/collect-firewall.sh`, and `scripts/cf-dns-route.sh`.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
