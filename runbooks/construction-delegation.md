---
summary: "Run substantial construction as Main on a Light/Medium/Heavy route — direct bounded specialist workers, let Testers verify independently, and open the PR without granting production authority."
trigger: "Do a substantial construction task / build X / implement or change X"
tier: "T1 build-time only"
executor: "Main directing native Codex specialist workers"
rollback: "git revert accepted repository changes"
---

# Runbook — construction delegation

**Tier:** T1 build-time only. The unprivileged `aliammar` account is the filesystem/OS construction boundary; Main and native workers use its ordinary capabilities without approval prompts. Workers receive no secrets, root grant, or production authority. `gh pr merge` and both repository `grant-root` spellings are hard-blocked. The authoritative route, role, capsule, ownership, verification, and repair rules are in [`../docs/conventions/construction.md`](../docs/conventions/construction.md); this runbook is the operational checklist for them.

## Preconditions

- Main owns the scoped success condition and can define the acceptance evidence for every delegated package — in Heavy that evidence is produced by an independent Tester, not by Main re-running the work.

## Verification discipline

Prefer canonical repository test commands and maintained fixtures for repeatable mutations; use
language-native temporary-directory lifecycle handling for disposable data. Production credentials,
trust tiers, destructive actions, root grants, and human merge remain separate authority boundaries.

## Steps

1. **Pick, mark, and load the route.** Light (Main works alone) is the default; use Medium or Heavy only for substantive work, and follow the route the active directive selected. For substantive Medium/Heavy, choose a unique lowercase underscore-safe deployment ID and put `<!-- skynet-deployment-start: <deployment_id> -->` in Main's first commentary message. Read the six compact `agent_docs/` files once plus the active directive before broad exploration; higher-authority sources always win conflicts. Do not infer Medium/Heavy merely because workers exist.
2. **Decompose into bounded packages with explicit, non-overlapping ownership.** Keep tightly-coupled architecture, contracts, and cross-package decisions with Main. Dependent packages may be delegated sequentially when ownership is clear; independence is not a precondition for delegating. In Light/Medium Main still implements and verifies; in Heavy Main assigns production to Executors and independent verification to Testers.
3. **Route the workers.** Companion (persistent read-only context) and Investigator (disposable read-only evidence) supply context; Default/Senior Executors own bounded implementation and ordinary repair; a Tester independently designs and runs verification. Concurrency is bounded by non-overlapping ownership, not a fixed worker count. Unresolved architecture/authority/risk decisions stay with Main.
4. **Write the capsule.** Open each initial assignment with a deployment-unique Task ID and the role's capsule (context, goal, guidance) — material context, contracts, boundaries, intended outcome, and cautions. Give the Tester acceptance intent, risks, and gates, not a test script. Tell every writer other workers share the repo and must preserve concurrent edits. Follow-ups repeat the Task ID and send only changed parts.
5. **Coordinate without noise.** Dispatch independent workers that inform one decision together and synthesise once; do not poll or request status-only updates. Spawn a worker only through the native Codex subagent mechanism, and only when the installed or project configuration exposes the requested role with the required model and effort; native workers inherit the no-prompt `aliammar` session posture. If the role is not exposed, stop and report the routing limitation rather than falling back to a legacy role. A worker report is not a merge signal.
6. **Repair through the owner.** An ordinary defect returns to the owning Executor and the same Tester rechecks it. In Heavy, Main evaluates the returned evidence and decides — it does not run the Tester's checks or make the Executor's edits; after a second evidence-free response, replace the worker or report the limitation. In Light/Medium Main implements and verifies directly.
7. **Close with one continuation.** Main owns acceptance intent, directive state, journal evidence, generated-view regeneration, integration decisions, the authored PR, and the three state-memory files (`project_progress.md`, `project_diary.md`, `latest_session_work.md`). An implementation-ready closure records the open authored PR as pending fresh review without claiming external acceptance or merge; paused keeps the phase; blocked records the external condition. Every shape leaves exactly one `## Next Entry Point` in latest-session memory. In Light/Medium Main runs declared checks; in Heavy it evaluates Tester evidence. Once Main seals implementation state, one Archivist finishes assigned stable memory/current docs and reports recorded usage with the project skill; it never estimates missing counts or edits Main-owned state. Main then commits, pushes, opens the authored PR, reports the PR number/URL, and **stops**. Ali manually starts acceptance review in a separate fresh chat/session against that open PR before merge; Ali does not supply or compare commit hashes. The reviewer resolves the target branch, current base/main SHA and PR head SHA from GitHub, reviews that exact integration pair, and resolves both again immediately before verdict. If either moved before verdict, it refreshes the affected review and cannot ACCEPT the stale pair. ACCEPT approves the exact pair verified immediately before the verdict. If either revision is known to change before human merge, ACCEPT becomes stale and fresh review is required. On the intended private GitHub Free setup, there is no mechanical/atomic guarantee that the reviewed pair remains unchanged between the reviewer's final recheck and Ali's later click-to-merge operation; prompt merge after ACCEPT reduces but does not eliminate that race window. Do not require a paid GitHub upgrade, manual SHA comparison, or a read-then-merge helper that falsely claims atomicity. A FIX returns to the original implementation/fix session, which updates the same PR and stops again. A bounded post-merge closeout records the approved review pair and actual merged result as distinct evidence plus final directive/archive state through the normal human-merged PR path; it does not automatically launch another acceptance review unless it introduces substantive implementation changes. A directive may define a one-time legacy integrated-state transition only for work already merged before this rule; any FIX from that transition opens a corrective PR and returns to the normal open-PR review lifecycle.

## Verify

- Each accepted package meets its stated acceptance criteria on the route's own evidence (Main's checks in Light/Medium; the independent Tester's in Heavy); the final PR includes the integrated tests and catalog/convention updates where required.
- An external ACCEPT records the reviewer-resolved base/main SHA and PR head SHA verified immediately before verdict. Known movement of either before merge makes it stale; GitHub mergeability or unchanged head alone is not evidence that the reviewed integration result is unchanged.
- On private GitHub Free, external ACCEPT is approval of that last-verified pair, **not** an atomic merge-time guarantee. The race window to later human merge is an explicit platform limitation.

## Rollback

- Revert accepted repository changes through the normal PR path. Stop if a package's scope or acceptance evidence cannot be established.

## Evidence

- Retain the capsules, reports, reviewed integration identity, verification output, directive/journal closure, token
  report or exact limitation, PR, and actual merged result. Human handoffs use the PR identity; agents resolve revision hashes themselves.
