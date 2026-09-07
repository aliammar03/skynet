---
summary: "Run substantial construction as a lead — route bounded helpers, verify their work, and open the PR without granting production authority."
trigger: "Do a substantial construction task / build X / implement or change X"
tier: "T1 build-time only"
executor: "Lead with bounded native helpers or bin/agent"
rollback: "git revert accepted repository changes"
---

# Runbook — construction delegation

**Tier:** T1 build-time only. Helpers have no secrets, tokens, grants, or production authority; their sandbox is their leash. The authoritative role, BIV, and tier rules are in [`../docs/conventions/construction.md`](../docs/conventions/construction.md).

## Preconditions

- The lead owns a scoped success condition and can independently verify every delegated result.

## Steps

1. **Assess for BIV work.** For substantial construction, proactively delegate only a chunk that is **Bounded** (one-sentence outcome), **Independent** (no continual decisions), and **Verifiable** (cheap inspection/test). Keep ambiguous architecture or tightly coupled work with the lead; do not create parallelism for its own sake.
2. **Use the authorized packet's execution lead.** Use Luna High for bounded Builder/Mechanic work and Luna Medium for read-only Scout work. Keep at most two helpers active and one delegation level. Unresolved architecture/recovery/policy decisions go to Astra Medium.
3. **Write the hand-off.** State the exact files/dirs, deliverable, write allowance (including “do not commit/push”), and verification commands. Tell every writer that other agents share the repo and they must preserve concurrent edits.
4. **Launch deliberately.** In a Codex lead session, use native bounded helpers. Other engines can use the equivalent:
   ```bash
   bin/agent scout "<scoped prompt>" --dry-run
   bin/agent scout "<scoped prompt>"
   bin/agent lead "<authorized packet>" --tier astra --dry-run
   ```
   `--cwd` is permitted only for an exact registered Skynet worktree. A helper report is not a merge signal.
5. **Integrate.** Re-read cited evidence, inspect each full writer diff, run the declared tests yourself, and make any necessary integration edits. The lead owns the resulting PR.
6. **Preserve continuity.** For a job crossing sessions, keep the compact ignored `.agent/CHECKPOINT.md`; delete it after durable facts move to their actual home. After human merge, use a fresh Astra Medium session for independent review and next-packet planning as required by the directive.

## Verify

- Each accepted result is within its stated scope and passes its verification; the final PR includes the integrated tests and catalog/convention updates where required.

## Rollback

- Revert accepted repository changes through the normal PR path. Stop if a helper’s scope or result cannot be verified.

## Evidence

- Retain the prompts, reports, reviewed diffs, verification output, and PR.
