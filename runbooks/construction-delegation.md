---
summary: "Run substantial construction as Main on a Light/Medium/Heavy route — direct bounded specialist workers, let Testers verify independently, and open the PR without granting production authority."
trigger: "Do a substantial construction task / build X / implement or change X"
tier: "T1 build-time only"
executor: "Main directing native Codex specialist workers"
rollback: "git revert accepted repository changes"
---

# Runbook — construction delegation

**Tier:** T1 build-time only. Workers have no secrets, tokens, grants, or production authority. A worker's filesystem reach is the **spawning session's** sandbox (Codex 0.153.4 does not apply a role file's own `sandbox_mode` per child); the Skynet project config pins that session sandbox to `workspace-write`, so no worker inherits `danger-full-access`. The authoritative route, role, capsule, ownership, verification, and repair rules are in [`../docs/conventions/construction.md`](../docs/conventions/construction.md); this runbook is the operational checklist for them.

## Preconditions

- Main owns the scoped success condition and can define the acceptance evidence for every delegated package — in Heavy that evidence is produced by an independent Tester, not by Main re-running the work.

## Verification without permission noise

For routine T1 verification of repo-local files and `$TMPDIR`/`tmp` scratch, Main and mutable
workers use the construction session's `workspace-write` boundary and must not request operator
escalation merely to create, mutate, or clean up that scratch. Prefer canonical repository test
commands and maintained test-suite fixtures for repeatable mutations; avoid many ad-hoc compound
shell probes. For one-off exploratory disposable fixtures, prefer language-native temporary-directory
lifecycle handling; if harmless TMP-only cleanup alone would require escalation, leave it for normal
automatic cleanup. Normal approval and human checkpoints still apply to credentials, production,
destructive actions, and every other actual authority boundary. The detailed rule lives in the
[construction convention](../docs/conventions/construction.md).

## Steps

1. **Pick and mark the route.** Light (Main works alone) is the default; use Medium or Heavy only for substantive work, and follow the route the active directive selected. For substantive Medium/Heavy, choose a unique lowercase underscore-safe deployment ID and put `<!-- skynet-deployment-start: <deployment_id> -->` in Main's first commentary message. Do not infer Medium/Heavy merely because workers exist.
2. **Decompose into bounded packages with explicit, non-overlapping ownership.** Keep tightly-coupled architecture, contracts, and cross-package decisions with Main. Dependent packages may be delegated sequentially when ownership is clear; independence is not a precondition for delegating. In Light/Medium Main still implements and verifies; in Heavy Main assigns production to Executors and independent verification to Testers.
3. **Route the workers.** Companion (persistent read-only context) and Investigator (disposable read-only evidence) supply context; Default/Senior Executors own bounded implementation and ordinary repair; a Tester independently designs and runs verification. Concurrency is bounded by non-overlapping ownership, not a fixed worker count. Unresolved architecture/authority/risk decisions stay with Main.
4. **Write the capsule.** Open each initial assignment with a deployment-unique Task ID and the role's capsule (context, goal, guidance) — material context, contracts, boundaries, intended outcome, and cautions. Give the Tester acceptance intent, risks, and gates, not a test script. Tell every writer other workers share the repo and must preserve concurrent edits. Follow-ups repeat the Task ID and send only changed parts.
5. **Coordinate without noise.** Dispatch independent workers that inform one decision together and synthesise once; do not poll or request status-only updates. Spawn a worker only through the native Codex subagent mechanism, and only when the installed or project configuration actually exposes the requested role with the required model and effort (filesystem sandbox is the session's, not the role's); if the role is not exposed, stop and report the routing limitation rather than falling back to a legacy role. A worker report is not a merge signal.
6. **Repair through the owner.** An ordinary defect returns to the owning Executor and the same Tester rechecks it. In Heavy, Main evaluates the returned evidence and decides — it does not run the Tester's checks or make the Executor's edits; after a second evidence-free response, replace the worker or report the limitation. In Light/Medium Main implements and verifies directly.
7. **Close with one continuation.** Main owns acceptance, directive state, journal evidence, generated-view regeneration, integration decisions, and the authored PR. Complete advances to the next-phase prompt; paused keeps the phase and records a same-phase prompt; blocked also sets directive status `blocked` and names the unblock condition. `.agent/CHECKPOINT.md` is optional disposable working state, never the entry point. In Light/Medium Main runs declared checks; in Heavy it evaluates Tester evidence. Once all other closure work is sealed, one Archivist finishes assigned docs and reports recorded usage with the project skill; it never estimates missing counts. After human merge, a fresh session reviews the merged result and returns a paste-ready fix prompt rather than repairing.

## Verify

- Each accepted package meets its stated acceptance criteria on the route's own evidence (Main's checks in Light/Medium; the independent Tester's in Heavy); the final PR includes the integrated tests and catalog/convention updates where required.

## Rollback

- Revert accepted repository changes through the normal PR path. Stop if a package's scope or acceptance evidence cannot be established.

## Evidence

- Retain the capsules, reports, reviewed diffs, verification output, directive/journal closure, token
  report or exact limitation, and PR.
