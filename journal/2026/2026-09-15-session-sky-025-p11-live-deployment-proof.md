---
date: 2026-09-15
time: 00:40:58            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P11 live deployment proof
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #259, vm-docker-dmz, librespeed]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: resolved     # none | open | resolved | unknown; digest shows only explicit open
resolves: [2026-09-15-session-sky-025-p11-deployment-orchestration-implementation]
---

# 2026-09-15 · session · SKY-025 P11 live deployment proof

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Resumed P11 PR #259 after the earlier live source pull had failed because Arcane's registered GitHub
credential was invalid. `gh auth status` confirmed the local CLI was authenticated as
`aliammar-skynet` with repository access; the credential value was never printed. A Python process
read it directly from `gh auth token`, sent it only in the Arcane repository-update request, and did
not write it to disk. Arcane's `/customize/git-repositories/<id>/test?branch=main` endpoint passed.

The first full `bin/skynet deploy service librespeed --repo /home/aliammar/skynet --branch main
--gate --json` run synced revision `f8072b390c10957a572eda4aa112da0583e46796` and atomically wrote the
10-key environment, owner `1000:1000`, but reported `malformed Arcane API response` at redeploy. A
read-only P10 verification immediately showed the exact revision live, one healthy container, and
`speed.aliammar.net` returning HTTP 200 with TLS verification result 0. Inspection of Arcane's upstream
handler showed redeploy returns an NDJSON activity/progress stream ending in `{"done":true}`, not the
ordinary `{success,data}` response expected by the client.

The executor added a bounded NDJSON redeploy consumer and bound the local Compose/env bytes to the
selected Git revision before any write. The final identical live command completed every stage and
returned `status=success`, `verification=runtime-complete-and-gate-passed`, and `recovery=not-needed`.

## Actions & outcomes
- Updated exactly one existing Arcane repository registration, ID
  `d3b4ceb8-2f53-4aec-afbb-c17dadc4a155`, using the authenticated local GitHub credential; Arcane
  connection test passed. No other repository or GitHub account setting changed.
- First post-credential deploy → source/environment/runtime were healthy, but P11 refused success
  because it parsed the streamed redeploy response as a normal JSON envelope.
- Added strict NDJSON terminal-success handling and selected-revision input binding; disposable
  success/error/malformed/timeout and dirty/untracked/symlink source cases were exercised.
- Final live deploy → repository selected, sync selected, source synced, environment replaced,
  redeploy requested, runtime reconciled, and report-only gate passed. One container was running and
  healthy; `speed.aliammar.net` returned 200 with valid TLS.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Treat Arcane redeploy as a normal JSON API request → abandoned because Arcane v2 intentionally
  streams activity/progress NDJSON and signals completion with one terminal `done=true` frame.
- Trust the working-tree service files merely because a branch name resolved → abandoned because a
  dirty or mismatched `.env` source could otherwise be deployed under a false commit identity.

## Follow-ups / open threads
- No live P11 blocker remains. PR #259 still requires fresh external review and same-PR accepted
  closeout before human merge.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
