---
summary: "Execute one directive phase on one PR: intake, implement, bin/check, update the directive status, open the PR, stop."
---

# Execute a directive phase

1. **Intake.** Read `AGENTS.md` and the directive named in the request. Its `## Status` block names
   the next phase. Read only the code, docs, and runbooks that phase touches.
2. **Branch.** Start from current `main`, or reuse the open PR for this phase if one exists. One
   phase is one PR.
3. **Plan.** For a phase with a live T2 step, post the AGENTS.md §2 plan (intent, hosts, rollback)
   and wait for approval before the live step. Everything else runs without narration.
4. **Implement** the phase's steps and nothing beyond them. Update callers, packaging, and current
   docs together. Add or update a test for every behavior added or fixed; a write path gets a
   failure-case test.
5. **Prove.** Run `bin/check`. Collect live evidence the phase's exit criteria ask for.
6. **Record progress in the same PR.** Flip the phase box, update the directive's `## Status` block
   and frontmatter (`current_phase`, `status`, `updated`), and run `bin/plan list`. Write a
   `journal/` episode only if something non-obvious happened.
7. **Open the PR** with: what and why (written to teach), the review tier (Light or Full) with the
   reason, the `bin/check` output, and live evidence. Then **stop**. Never review or merge it.

If blocked, set the directive `status: blocked`, write the exact unblock condition in its
`## Status` block, and push that on the same PR.
