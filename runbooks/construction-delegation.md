---
summary: "Run substantial construction as Main on a Light/Medium/Heavy route — direct bounded specialist workers, let Testers verify independently, and open the PR without granting production authority."
trigger: "Do a substantial construction task / build X / implement or change X"
tier: "T1 build-time only"
executor: "Main directing native specialist workers or bin/agent"
rollback: "git revert accepted repository changes"
---

# Runbook — construction delegation

**Tier:** T1 build-time only. Workers have no secrets, tokens, grants, or production authority; their sandbox is their leash. The authoritative route, role, capsule, ownership, verification, and repair rules are in [`../docs/conventions/construction.md`](../docs/conventions/construction.md); this runbook is the operational checklist for them.

## Preconditions

- Main owns the scoped success condition and can define the acceptance evidence for every delegated package — in Heavy that evidence is produced by an independent Tester, not by Main re-running the work.

## Steps

1. **Pick the route.** Light (Main works alone) is the default; use Medium or Heavy only for substantive work, and follow the route the active directive selected. Do not infer Medium/Heavy merely because workers exist.
2. **Decompose into bounded packages with explicit, non-overlapping ownership.** Keep tightly-coupled architecture, contracts, and cross-package decisions with Main. Dependent packages may be delegated sequentially when ownership is clear; independence is not a precondition for delegating. In Light/Medium Main still implements and verifies; in Heavy Main assigns production to Executors and independent verification to Testers.
3. **Route the workers.** Companion (persistent read-only context) and Investigator (disposable read-only evidence) supply context; Default/Senior Executors own bounded implementation and ordinary repair; a Tester independently designs and runs verification. Concurrency is bounded by non-overlapping ownership, not a fixed worker count. Unresolved architecture/authority/risk decisions stay with Main.
4. **Write the capsule.** Open each initial assignment with a deployment-unique Task ID and the role's capsule (context, goal, guidance) — material context, contracts, boundaries, intended outcome, and cautions. Give the Tester acceptance intent, risks, and gates, not a test script. Tell every writer other workers share the repo and must preserve concurrent edits. Follow-ups repeat the Task ID and send only changed parts.
5. **Coordinate without noise.** Dispatch independent workers that inform one decision together and synthesise once; do not poll or request status-only updates. Launch a worker only when the installed native or `bin/agent` configuration actually exposes the requested SKY-026 role (`--dry-run` first; `--cwd` only for a registered Skynet worktree); if the role is not exposed, stop and report the routing limitation rather than falling back to a legacy role. A worker report is not a merge signal.
6. **Repair through the owner.** An ordinary defect returns to the owning Executor and the same Tester rechecks it. In Heavy, Main evaluates the returned evidence and decides — it does not run the Tester's checks or make the Executor's edits; after a second evidence-free response, replace the worker or report the limitation. In Light/Medium Main implements and verifies directly.
7. **Integrate and open the PR.** Main owns integration decisions and the authored PR: in Light/Medium it runs the declared checks itself; in Heavy it evaluates the Tester's returned evidence against the acceptance criteria rather than re-verifying. For a job crossing sessions keep the compact ignored `.agent/CHECKPOINT.md`; delete it after durable facts move to their canonical home. After human merge, a fresh session reviews the merged result and returns a paste-ready fix prompt rather than repairing.

## Verify

- Each accepted package meets its stated acceptance criteria on the route's own evidence (Main's checks in Light/Medium; the independent Tester's in Heavy); the final PR includes the integrated tests and catalog/convention updates where required.

## Rollback

- Revert accepted repository changes through the normal PR path. Stop if a package's scope or acceptance evidence cannot be established.

## Evidence

- Retain the capsules, reports, reviewed diffs, verification output, and PR.
