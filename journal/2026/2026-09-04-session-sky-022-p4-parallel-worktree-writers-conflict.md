---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-022 P4 — parallel worktree writers + conflict
tier_touched: [T1]
grants: []
refs: [SKY-022, "PR (phase/sky-022-p4)", bin/agent, git-worktree, tests/agent-test.sh, tests/gitignore-test.sh]
---

# 2026-09-04 · session · SKY-022 P4 — parallel worktree writers + conflict

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used. -->

## What happened
Executed SKY-022 Phase 4 (parallel writers via git worktree) — the first phase with TWO active
helpers at once. Same cross-vendor shape: Claude lead, real Codex Builder helpers.

Enabling tool first: added `--cwd <dir>` to `bin/agent` (lead work, commit b8ef0af). It roots the
codex run at a worktree via `-C <dir>`; default (main checkout) behavior unchanged. bin/agent had
always `cd`'d to the main repo, so it could not target a worktree.

Set up: two worktrees off the phase HEAD —
`git worktree add -b p4-agent-test /home/aliammar/skynet-p4-a phase/sky-022-p4` and
`... -b p4-gitignore-test /home/aliammar/skynet-p4-b ...`.

Two genuinely independent writer tasks, launched CONCURRENTLY (both `bin/agent builder "<prompt>"
--cwd <worktree>`, gpt-5.6-terra high):
- Writer A → `tests/agent-test.sh` (unit-test bin/agent role→tier/model/effort/sandbox resolution via
  --dry-run; 32 assertions). Both also wired their test into `.githooks/pre-commit` +
  `.github/workflows/checks.yml`, appending after the same `construction-test` line — the engineered
  conflict.
- Writer B → `tests/gitignore-test.sh` (guards the P3 invariant that `.agent/` stays gitignored; 3
  assertions via `git check-ignore`).

Both writers finished, both tests green in their worktrees — but BOTH reported **"commit blocked"**.
Cause (the P4 finding): a linked worktree's git metadata lives under the MAIN repo's
`.git/worktrees/<name>/` (index.lock etc.), which is OUTSIDE the worktree dir the `workspace-write`
sandbox is rooted at. So a sandboxed helper physically cannot commit in a worktree — it can only
write the worktree's working tree. Resolution, consistent with the trust boundary: **helpers write,
the lead commits.** The lead (unsandboxed) committed each writer's diff on its branch (A=55268f6,
B=4b8bc5a).

Integration via plain git on the phase branch:
- `git merge --no-ff p4-agent-test` → clean (5049d4c).
- `git merge --no-ff p4-gitignore-test` → CONFLICT on `.githooks/pre-commit` AND
  `.github/workflows/checks.yml` (both writers appended at the same spot). Lead resolved by hand —
  kept BOTH registrations in a stable order — `git add` + `git commit` (d192f2f). No orchestration
  layer; ordinary git tools.

Verified: full suite green on the integrated branch — check-invariants + all 9 test suites
(entity/digest/dns-revert/compose-rollback/tofu-rollback/collect-pbs/construction/agent/gitignore).
Tidied the pre-commit header (gates 6-7) and documented worktree-by-exception + helpers-write/lead-
commits in construction.md (10257d9). Tore down both worktrees (`git worktree remove`) and deleted
the merged branches (`git branch -d` succeeded = fully merged).

## Actions & outcomes
- bin/agent --cwd added + validated (dry-run: -C set; bad dir fails closed) → b8ef0af.
- 2 worktrees + 2 branches off phase HEAD.
- 2 concurrent Builders → correct diffs in isolated worktrees, tests pass; commit blocked by sandbox.
- Lead committed each branch; merged A clean, merged B → conflict → resolved by hand (kept both).
- Full suite 9/9 + invariants green; docs + hook header updated; worktrees + branches cleaned up.

## Graveyard — tried & abandoned
- **Helper commits its own branch in the worktree** → abandoned; `codex --sandbox workspace-write
  -C <worktree>` cannot write `<main>/.git/worktrees/<name>/index.lock` (git metadata is outside the
  sandbox root). Not worth widening the sandbox with `--add-dir <main>/.git/...` — that punches a hole
  in the leash for a cosmetic "helper committed it" credit. Lead-commits is the right model.

## Follow-ups / open threads
- If a future task truly needs helpers to commit in-worktree, the option is `codex --add-dir
  <main>/.git/worktrees/<name>` — but only if it clearly pays; default stays helpers-write/lead-commits.
- P5 next: dogfood ≥5 real construction tasks across the role/parallelism matrix, capture only useful
  observations, then decide at phase close what (if anything) deserves more automation before P6
  (thin Codex App Server adapter).
- Still-open ping-latency friction from P3 (watcher poll granularity) — cosmetic; not addressed
  structurally.
