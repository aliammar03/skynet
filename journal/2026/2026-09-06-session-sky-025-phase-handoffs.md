---
date: 2026-09-06
time: "09:03"
kind: session
title: "Add SKY-025 execute and review handoffs"
tier_touched: [T1]
grants: []
refs: [SKY-025]
thread_status: open
---

## What happened

Ali asked to implement the two reusable prompts and GitHub PR workflow. GitHub reported #208
merged into main at 0616dfa9f5602375cd43b5cf1ec0a83e8edfd6df. Started
`plan/sky-025-phase-handoffs` from that revision.

## Actions & outcomes

Added `planning/prompts/execute.md` and `review.md`, each with a PR body contract, and a README
with the manual session/merge sequence. Replaced SKY-025's inline prompts with invocations and
linked the workflow from planning/README.md. Review records implementation/fix merge SHAs and
reviewed main; its planning PR releases only the accepted next packet or bounded fixes.
No overhaul phase was executed and no live service was changed.

## Graveyard — tried & abandoned

None. The workflow uses manual fresh tasks and existing GitHub PRs; no launcher or CI workflow
was built for this documentation request.

## Follow-ups / open threads

Ali merges the workflow PR, then starts the detailed Phase 1 in Astra Medium using the execute prompt.
