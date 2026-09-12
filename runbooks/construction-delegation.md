---
summary: "Run substantial construction as Main on a Light/Medium/Heavy route — direct bounded specialist workers, let Testers verify independently, and close accepted work on the same PR before one human merge."
trigger: "Do a substantial construction task / build X / implement or change X"
tier: "T1 build-time only"
executor: "Main directing native Codex specialist workers"
rollback: "git revert accepted repository changes"
---

# Runbook — construction delegation

**Tier:** T1 build-time only. The unprivileged `aliammar` account is the filesystem/OS construction boundary; Main and native workers use its ordinary capabilities without approval prompts. Workers receive no secrets, root grant, or production authority. `gh pr merge` and both repository `grant-root` spellings are hard-blocked. The authoritative route, role, capsule, ownership, verification, review, and closeout rules are in [`../docs/conventions/construction.md`](../docs/conventions/construction.md); this runbook is the operational checklist for them.

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
7. **Publish and stop for fresh review.** Main owns acceptance intent, directive state, journal evidence, generated-view regeneration, integration decisions, the authored PR, and the three state-memory files (`project_progress.md`, `project_diary.md`, `latest_session_work.md`). Before external review, record the open PR as pending fresh review without claiming external acceptance or merge. Once Main seals implementation state, one Archivist may finish assigned stable memory/current docs and report recorded usage; it never estimates missing counts or edits Main-owned state. Main commits, pushes, opens the authored PR, reports its number/URL, and **stops**. Ali manually starts a separate fresh reviewer and supplies only the PR identity.
8. **Review the open PR.** Reviewer resolves current target/base SHA + PR-head SHA, reviews that exact integration result, and resolves both again immediately before verdict. FIX returns one paste-ready prompt; original session repairs the same PR, republishes, and stops for another fresh review. ACCEPT approves the exact last-verified pair and posts a machine-readable acceptance marker to the PR conversation containing scope, reviewed base, reviewed head, and `verdict=ACCEPT`. The reviewer does not edit Git content.
9. **Close accepted work on the same PR.** Ali only tells the original implementation/fix session that the PR was accepted. Main fetches the acceptance marker itself, confirms the PR is still open, confirms current base equals reviewed base and current head equals reviewed head, then enters accepted closeout mode. Allowed Git changes are only: accepted directive status/archive move; planning index/roadmap/state-map updates; `agent_docs/project_progress.md`, `project_diary.md`, `latest_session_work.md`; append-only journal closure evidence; and generator-owned closure views refreshed only because state changed. No source/runtime/config/test/invariant/AGENTS/doctrine/runbook/behavioral-doc/stable-memory or other substantive change is allowed. Main proves `reviewed head..final head` is closeout-only. Any other change, unexplained head movement, or reviewed-base movement invalidates ACCEPT and requires fresh review.
10. **Merge once.** Push the bounded closeout to that same accepted PR, let CI finish, recheck base and closeout-only delta, report the PR ready, and stop. Ali human-merges the same PR once. **Never create a closeout-only PR.** No second acceptance review is required for a valid closeout-only delta. Private GitHub Free still leaves a race window between the final recheck and Ali's click-to-merge; prompt merge minimizes but does not eliminate it. Do not ask Ali to compare hashes and do not invent a helper that claims atomicity.

A directive may define a one-time legacy integrated-state transition only for work already merged before this lifecycle. If that legacy review ACCEPTs and a next implementation PR naturally follows, carry the legacy closeout bookkeeping into the next PR rather than creating a standalone closeout PR. A legacy FIX opens one corrective PR and immediately returns to the normal open-PR lifecycle.

## Verify

- Each implementation package meets its stated acceptance criteria on the route's own evidence (Main's checks in Light/Medium; independent Tester in Heavy).
- External ACCEPT records and comments the reviewer-resolved base+head pair immediately before verdict.
- Before accepted closeout starts, Main independently matches current base/head to that marker.
- Every post-ACCEPT Git change is inside the closeout-only envelope; otherwise fresh review is mandatory.
- The final accepted PR receives one human merge; there is no post-merge closeout PR.
- On private GitHub Free, the final recheck-to-click race remains explicit and non-atomic.

## Rollback

- Revert accepted repository changes through the normal PR path. Stop if a package's scope or acceptance evidence cannot be established.

## Evidence

- Retain capsules, worker reports, independent verification, reviewer acceptance marker, closeout-only delta proof, directive/journal closure, token report or exact limitation, PR, and final merged result. Human handoffs use the PR identity; agents resolve revision hashes themselves.
