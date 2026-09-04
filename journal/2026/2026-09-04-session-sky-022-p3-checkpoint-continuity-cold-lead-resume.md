---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-022 P3 — checkpoint continuity + cold-lead resume
tier_touched: [T1]
grants: []
refs: [SKY-022, "PR (phase/sky-022-p3)", .agent/CHECKPOINT.md, runbooks/construction-delegation.md, bin/agent]
---

# 2026-09-04 · session · SKY-022 P3 — checkpoint continuity + cold-lead resume

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used. -->

## What happened
Executed SKY-022 Phase 3 (lightweight continuity). Same cross-vendor shape as P2: this session is
the Claude lead; the resume was delegated to a real Codex lead via `bin/agent lead`.

Convention machinery first:
- `.gitignore`: added `.agent/` (the lead's disposable checkpoint). Confirmed `git check-ignore
  .agent/CHECKPOINT.md` hits and the tree stays clean.
- `docs/conventions/construction.md`: replaced the "detailed in Phase 3" placeholder in the
  continuity bullet with the actual compact CHECKPOINT.md shape (Goal / Done / Current / Decisions /
  Dead ends / Verified / Next) + the write-triggers (milestone / handoff / blocker / before ending a
  long session — not every command).

The dogfood (the real test — prove a cold lead resumes from the checkpoint alone):
- Chose a real bounded two-milestone task: write `runbooks/construction-delegation.md` (the
  procedure P1/P2 built tooling for but never catalogued).
- **M1 (this lead):** wrote the runbook body (sections 1-6) with `## 7. Worked example` left as an
  explicit TODO stub, and deliberately did NOT register it in `runbooks/README.md`. Committed as
  e7beeaa so the tree was clean before the resume.
- Wrote `.agent/CHECKPOINT.md` in the 7-field shape. "Next" = (1) fill §7 from the P2 journal
  episode, (2) register the catalog row; edit only those 2 files, don't commit.
- **M2 (fresh cold Codex lead):** `bin/agent lead "<resume-from-checkpoint>"` — first exercise of the
  `lead` role path (terra, xhigh, workspace-write). The prompt gave it NO next-step content — only
  "read `.agent/CHECKPOINT.md` and do its Next step, honoring scope limits." Codex auto-loads
  AGENTS.md natively, so the cold lead's entire context was AGENTS.md + the checkpoint + git state.
- Result: it filled §7 with a faithful, concise P2 worked example (TODO removed), added a new
  "## Build & collaboration" catalog section in `runbooks/README.md`, touched ONLY those 2 files,
  ran the tests itself, and did NOT commit (HEAD stayed e7beeaa). Exactly the checkpoint's Next step.
- Lead verified: read both diffs, confirmed cross-links resolve, ran the full gate suite green,
  committed as M2 (06a231b).
- Disposed `.agent/CHECKPOINT.md` (durable facts now in the runbook + this journal + git). Gitignored,
  so its removal is a no-op to the tree — the point: it was never truth.

## Actions & outcomes
- `.gitignore` + construction.md continuity shape → committed e7beeaa (M1).
- `bin/agent lead` dry-run → resolved terra/xhigh/workspace-write correctly (lead path works).
- Cold lead run → completed both Next steps from the checkpoint alone; stayed in scope; no commit.
- Lead verify → 7/7 test suites + check-invariants green; links OK → committed 06a231b (M2).
- Checkpoint deleted; tree clean.

## Graveyard — tried & abandoned
- — nothing abandoned — (the resume worked first try; no dead ends this task).

## Follow-ups / open threads
- The cold lead was terra **xhigh** for a doc-fill — heavier effort than the task needed, but the
  point was to exercise the `lead` role path + prove checkpoint sufficiency, not to optimize cost.
  A real resume would pick effort by the remaining work's difficulty.
- Ping latency (Ali's observation): the `run_in_background` watcher fires a completion notification,
  but the `sleep`-poll granularity means a manual ping usually beats it — the work is already
  done-and-waiting. Not broken, just laggy. Tighten the poll or accept the ping race.
- P4 next: parallel writers on `git worktree` — the first phase that needs two ACTIVE helpers at
  once (P1/P2/P3 each ran ≤1 helper at a time). Exercise an intentional conflict and confirm the
  lead resolves it with plain git, not an orchestration layer.
