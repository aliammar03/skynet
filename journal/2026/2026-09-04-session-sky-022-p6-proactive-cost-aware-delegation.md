---
date: 2026-09-04
kind: session
title: SKY-022 P6 — proactive cost-aware delegation
tier_touched: [T1]
grants: []
refs: [SKY-022, "PR (phase/sky-022-p6)", docs/conventions/construction.md, runbooks/construction-delegation.md]
---

# 2026-09-04 · session · SKY-022 P6 — proactive cost-aware delegation

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used. -->

## What happened

Ali asked only to continue SKY-022 at the next phase and preserve its one-lead, shallow-delegation,
and complexity-must-be-earned doctrine. The directive resolved the next phase to P6. The lead read
the cold-boot digest, context map, planning mechanics, directive, system-design trust boundary,
construction doctrine/runbook, P5 raw episode, git state, helper definitions, and construction
tests. No production host, API, credential, or grant was used.

Before changing the doctrine, the lead treated P6 as substantial construction and launched two
native helpers concurrently without Ali asking for delegation. A Luna Scout received a read-only
audit: find stale conservative/default-single-agent wording, distinguish active App Server plans
from append-only journal history, map existing helper enforcement, and recommend the minimum edit
surface. A Terra Builder received two files only: `docs/conventions/construction.md` and
`runbooks/construction-delegation.md`; it was told to implement proactive BIV routing while
preserving lead ownership, one-level depth, the two-helper cap, native-first tooling, sandboxes,
production isolation, and earned complexity. Neither helper spawned another helper. The Builder
did not commit or touch any file outside its assignment.

The Scout and Builder independently converged on the same two-file edit surface. The Builder's first
patch was usable as returned and needed no corrective helper round. The Scout also found four old
journal episodes that describe App Server as a possible later phase. The lead left those files
unchanged because journal episodes are append-only raw evidence. Active SKY-022 text already records
that the App Server phase was rejected before execution and is not the next step.

The lead kept the directive status bump, roadmap refresh, journal entry, diff inspection, and final
verification. Those close-out edits were small, coupled to lead accountability, and cheaper to do
directly than to specify and verify through another helper.

## Actions & outcomes

- Luna Scout → read-only audit with file/line citations; no writes; identified the exact stale
  doctrine/runbook paragraphs and the existing invariant/test commands.
- Terra Builder → changed only the construction doctrine and delegation runbook; ordinary task
  intent now triggers proactive BIV assessment for substantial work; tiny work stays lead-only.
- Lead → inspected the complete diff, retained append-only journal history, closed P6 and SKY-022,
  refreshed the roadmap, and ran focused plus full repository gates.
- `bash tests/agent-test.sh` → 39 passed, 0 failed.
- `bash tests/construction-test.sh` → 8 passed, 0 failed.
- `./scripts/check-invariants.sh` → all machine-checkable hard laws held, including helper cap and
  sandbox declarations.

## Graveyard — tried & abandoned

- Editing old P1/P2/P4/P5 journal references to App Server → rejected because raw journal episodes
  are append-only; the new P6 episode records that the proposed phase was dropped.
- Adding a prose-string test merely to create a coding task for the Terra Builder → rejected because
  proactive judgement is manual doctrine and a brittle phrase assertion would be unearned machinery.
- Adding an App Server adapter, scheduler, queue, ledger, retry layer, or wider helper cap → no
  observed coordination failure justified any of them.

## Follow-ups / open threads

- — none; SKY-022 exit criteria passed.
