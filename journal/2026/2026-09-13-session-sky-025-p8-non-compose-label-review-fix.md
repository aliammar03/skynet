---
date: 2026-09-13
time: 10:37:13            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P8 non-Compose label review fix
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #255"] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P8 non-Compose label review fix

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali returned the independent review finding to the original implementation session. The reviewer
showed that `src/skynet/entities.py::_service_records` called `_string` with its required default and
raised `EntityError` whenever a Docker container lacked a `com.docker.compose.project` label. The
Docker collector intentionally records standalone containers with empty labels, and the previous
shell audit ignored containers outside the Compose-project domain.

The owning entity Executor changed `_service_records` to accept missing/empty string labels and skip
strings without the Compose project label. Non-string label values still raise `EntityError`.
Independent verification used disposable repositories only; no live endpoint or credential was used.

## Actions & outcomes
- Added empty-label and unrelated-label cases → both were ignored and did not create service rows.
- Added non-string label cases (`[]`, `{}`, `42`, `True`) → each remained a malformed-source error.
- Added `com.docker.compose.project=outside` without `compose/outside/` → audit returned failure with
  `svc/outside` in the `running-unmapped` bucket.
- Focused entity/cache/route/CLI/collection tests → 95 passed.
- Supported full pytest → 329 passed; packaged Nix checks passed.
- Entity shell compatibility → 47/47; hard invariants, construction (44), repository-surface (12),
  Ruff, strict mypy, and `git diff --check` passed.

## Graveyard — tried & abandoned
- Treating every collected Docker container as a Compose service candidate → abandoned because the
  collector's valid domain includes standalone/non-Compose containers.

## Follow-ups / open threads
- Publish the repair to PR #255 and stop for a fresh independent review.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
