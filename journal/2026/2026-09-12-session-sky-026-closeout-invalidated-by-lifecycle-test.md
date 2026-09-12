---
date: 2026-09-12
time: 22:04:00
kind: session
title: SKY-026 closeout invalidated by lifecycle test
tier_touched: [T1]
grants: []
refs: [SKY-026, PR-253, 2026-09-12-session-sky-026-accepted-same-pr-closeout]
thread_status: open
---

# 2026-09-12 · session · SKY-026 closeout invalidated by lifecycle test

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened

The first SKY-026 same-PR accepted closeout on PR #253 reached its final CI gate after Main had validated
the reviewer marker, moved the directive to `planning/archive/`, updated only sanctioned bookkeeping,
and proved the initial post-ACCEPT diff contained only closeout-allowed paths.

GitHub Actions run #657 passed hard invariants, `git diff --check`, digest, construction, rollback,
provisioning, and nightly gates, but the focused lifecycle suite failed four tests. Three failures were
`FileNotFoundError` from `tests/test_agent_docs.py` reading the old hard-coded path
`planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md` after the valid
closeout had moved that directive to `planning/archive/`. The fourth failure was a brittle wording check
requiring the literal word `race` in `latest_session_work.md` even though the handoff still stated the
same private-GitHub-Free non-atomic limitation.

The archive-path failure meant the accepted implementation had not actually tested its own legitimate
closeout transition. Fixing `tests/test_agent_docs.py` is a substantive post-ACCEPT change, so Main did
not treat it as closeout bookkeeping. The previous ACCEPT marker was declared stale and no merge was
attempted.

The repair changed the lifecycle regression suite to resolve SKY-026 from exactly one of two valid
locations: the active `planning/projects/` path while in progress, or the `planning/archive/` path after
accepted closeout. A new contract asserts that exactly one location exists, preventing a compatibility
duplicate from hiding the bug. Acceptance-state/race assertions were also made semantic enough to work
across implementation-ready and accepted-closeout state without weakening the private-Free limitation.

Because ACCEPT became stale, SKY-026 was returned from archive to the active project path with
`status: in-progress`, `current_phase: 4`, and P5 marked implementation-repaired / fresh-review-required.
The roadmap and Main-owned progress/diary/latest memory were restored to that truthful state. The prior
accepted-closeout journal episode remains append-only history of the attempted closeout and its pending
final-CI follow-up; this episode records why that attempt did not complete.

## Actions & outcomes

- Final closeout run #657 → safety/invariant lanes passed; focused lifecycle suite exposed the archive-
  transition test defect.
- No fake active-path duplicate was created to appease tests.
- `tests/test_agent_docs.py` → lifecycle path now follows exactly one active-or-archived SKY-026 file.
- Previous ACCEPT → stale because the test repair is substantive.
- SKY-026 directive + roadmap + Main-owned state → returned to P5 in-progress pending fresh review.
- PR #253 remains the one authored PR; no replacement or closeout-only PR was created.
- No production host, root grant, secret, service/timer, inventory, merge, or live infrastructure write
  occurred.

## Graveyard — tried & abandoned

- Leaving a duplicate pointer/copy at the old active path → rejected because planning doctrine requires
  one directive location and a duplicate would merely conceal the test defect.
- Treating test repair as bookkeeping → rejected because tests are explicitly substantive after ACCEPT.
- Merging on the old reviewer marker despite failed final CI → rejected; the stale-ACCEPT path exists
  specifically to prevent that.

## Follow-ups / open threads

- Require green focused lifecycle tests and full repository CI on the repaired #253 head.
- Run a new fresh external review of open PR #253. The previous acceptance marker must not be reused.
- On new ACCEPT, Ali returns to the original implementation session with only `accepted`; Main reruns
  bounded same-PR closeout and final CI before handing #253 back for one human merge.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
