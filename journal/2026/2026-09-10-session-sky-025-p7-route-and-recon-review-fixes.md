---
date: 2026-09-10
time: 00:00:02            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P7 route and recon review fixes
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #235", "PR #236", "PR #237", src/skynet/routes.py, src/skynet/recon.py]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-10 · session · SKY-025 P7 route and recon review fixes

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started from merged remote main `ded7289ca3938c3adeeaf21d3dad3bb90dcd5a80` after the Phase 7
implementation PRs #235, #236 and #237. Review findings showed that `routes.snapshot()` converted a
missing `compose/caddy-apps/Caddyfile` into an empty, successful zero-route result, and its parser
dropped an unclosed vhost block. Successful `recon --json` reports also lacked `target` and
`outcome`. This was a source/test-only correction in an isolated worktree; no collector was run
against production during the packet.

## Actions & outcomes
- Changed missing/unreadable Caddyfile handling to `CollectionError("route source unavailable", 3)`;
  atomic publication therefore retains previous route bytes.
- Made the Caddy block parser reject an unmatched closing brace or an unclosed vhost block rather
  than returning a partial route list.
- Added a regression with an actually nonexistent `Caddyfile` path and a regression with one
  complete then one truncated vhost block; both retain prior output and return non-success.
- Added `target: recon` and `outcome: success` to successful recon JSON while retaining its
  metadata and sections; unavailable responses remain unchanged.
- Focused `pytest -q tests/test_routes.py tests/test_recon.py` → 16 passed; focused Ruff and mypy
  passed.
- `nix develop --no-write-lock-file -c pytest -q` → 258 passed.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` → passed.
- `nix develop --no-write-lock-file -c mypy src/skynet` → passed.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → passed.
- `nix flake check --no-write-lock-file --no-build` → passed with existing system-rename,
  app-metadata and custom-deploy-output warnings.
- Staged `.githooks/pre-commit` → exit 0: invariant and shell suites passed, then 258 pytest
  tests, Ruff and mypy passed; `git diff --cached --check` → exit 0.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Treat an absent Caddyfile as a valid empty static source → abandoned because it establishes false
  fresh evidence and bypasses retained-snapshot failure behavior.

## Follow-ups / open threads
- Open the bounded P7 fix PR, then await human merge and a fresh review of the complete P7 merged
  result. Accepted progress remains 6/24.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
