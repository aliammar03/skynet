---
summary: "Run substantial construction as Main on a Light/Medium/Heavy route — direct bounded specialist workers, verify independently, and open the PR without granting production authority."
trigger: "Do a substantial construction task / build X / implement or change X"
tier: "T1 build-time only"
executor: "Main directing native specialist workers or bin/agent"
rollback: "git revert accepted repository changes"
---

# Runbook — construction delegation

**Tier:** T1 build-time only. Workers have no secrets, tokens, grants, or production authority; their sandbox is their leash. The authoritative route, role, capsule, and tier rules are in [`../docs/conventions/construction.md`](../docs/conventions/construction.md).

## Preconditions

- Main owns a scoped success condition and can independently verify every delegated result.

## Steps

1. **Pick the route.** Light (Main works alone) is the default; use Medium or Heavy only for substantive work, and follow the route the active directive selected. Do not infer Medium/Heavy merely because workers exist.
2. **Delegate only Bounded/Independent/Verifiable packages.** For substantive work, hand a worker only a chunk with a one-sentence outcome, no continual decisions, and cheap verification. Keep ambiguous architecture and tightly coupled decisions with Main.
3. **Route the workers.** Companion (persistent read-only context) and Investigator (disposable read-only evidence) supply context; Default/Senior Executors own bounded implementation and repair; a Tester independently verifies. Concurrency is bounded by non-overlapping ownership, not a fixed helper count. Unresolved architecture/authority/risk decisions stay with Main.
4. **Write the capsule.** Open each initial assignment with a deployment-unique Task ID and the role's capsule (context, goal, guidance) — exact files/dirs, deliverable, write allowance (including “do not commit/push”), and boundaries. Tell every writer other workers share the repo and must preserve concurrent edits. Follow-ups repeat the Task ID and send only changed parts.
5. **Coordinate without noise.** Dispatch independent workers that inform one decision together and synthesise once; do not poll or request status-only updates. Launch native bounded workers in a Codex session; other engines use the equivalent `bin/agent` routing (`--dry-run` first; `--cwd` only for a registered Skynet worktree). A worker report is not a merge signal.
6. **Repair through the owner.** An ordinary defect returns to the owning Executor and the same Tester rechecks it; Main does not take over implementation or verification. After a second evidence-free response, replace the worker or report the limitation.
7. **Integrate and preserve continuity.** Re-read cited evidence, inspect each full writer diff, run the declared checks yourself, and make integration edits — Main owns the PR. For a job crossing sessions keep the compact ignored `.agent/CHECKPOINT.md`; delete it after durable facts move to their canonical home. After human merge, a fresh session reviews the merged result and returns a paste-ready fix prompt rather than repairing.

## Verify

- Each accepted result is within its stated scope and passes its verification; the final PR includes the integrated tests and catalog/convention updates where required.

## Rollback

- Revert accepted repository changes through the normal PR path. Stop if a worker’s scope or result cannot be verified.

## Evidence

- Retain the capsules, reports, reviewed diffs, verification output, and PR.
