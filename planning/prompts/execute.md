---
summary: "Execute one authorized SKY-025 phase or fix packet, publish its authored PR, hand off for manual review, then stop."
---

# Execute one packet

> Execution prompt for the [phase handoff workflow](README.md). Follow the active SKY-025 directive
> and [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

Execute the next authorized SKY-025 packet, or the phase/slice specified by Ali.

1. Read `agent_docs/` once with AGENTS.md and planning/README.md before broad exploration. Locate the
   single active SKY-025 directive by ID (`bin/plan show SKY-025`, or tracked files if that helper has
   been replaced). Read its current packet, disposition map if present, and relevant conventions.
   Load other files only as needed.
2. Resolve current remote main and start a clean branch from it; preserve unrelated local work.
   Record the base SHA. Verify the phase authorization is merged, its preceding numbered phase accepted,
   and there is no outstanding FIX/BLOCKED review. Phase 1 is the bootstrap exception: its merged
   detailed packet needs no predecessor review. If an implementation/fix PR already exists for this
   packet, inspect and reuse that same branch/PR rather than duplicating it. For remaining slices within
   an authorized phase, Main details the next bounded packet before work. Completed slices need no
   independent phase review; preserve human merge and live/grant prerequisites. Never advance to the
   next numbered phase without phase acceptance.
3. Confirm the session's model/effort matches the packet. Follow the directive's routing rules;
   do not claim a model switch or silently substitute an unavailable model. Route the session on a
   Light/Medium/Heavy route and delegate workers, capsules, ownership, batching, and verification
   through [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md). The
   phase table's route is guidance for the Main session, not a second orchestration system.
4. Implement only this 1–2h packet, including affected callers, tests, and current documentation.
   Follow its live boundaries and existing authorization. Downtime tolerance does not expand data,
   credential, or privilege authority. If the scope no longer fits, propose a bounded slice and
   record unfinished exits; do not quietly expand scope or declare the phase complete.
5. Verify per the construction convention: in Light/Medium run the packet's meaningful checks
   yourself; in Heavy evaluate the independent Tester's returned evidence against the exit criteria
   rather than re-running its checks, and return ordinary defects to the owning Executor. Report exact
   commands, results, skipped/unavailable checks, and temporary breakage. Do not invent validation or
   weaken an exit criterion. Escalate unresolved architecture/recovery decisions according to the directive.
6. Record implementation closeout evidence as the directive requires. Record slice and full-phase status
   separately; do not increment accepted progress, accept your own phase, or flesh out dependent numbered
   phases. A completed numbered phase is **implementation ready / pending fresh review**, not accepted.
   Update Main-owned `agent_docs` state truthfully: an open PR is open, not merged or externally accepted.
   Commit and push the scoped changes and open the authored PR to main. Never merge it.
7. Report the PR URL, exact head SHA, checks/results, limitations, and the review handoff, then **STOP**.
   Do not start, spawn, or continue into final acceptance review. Ali manually starts that review in a
   separate fresh chat against the open PR.

Use this PR title: `SKY-025 P<N>: <outcome>` (or `SKY-025 P<N> fix: <outcome>`).
Use these compact PR body fields; replace placeholders with evidence:

```text
Packet: <phase/slice; merged planning/closeout authority or bootstrap directive commit>
Base: <full main SHA>
Why and changes: <problem, implemented behavior, affected callers/docs>
Exit evidence: <each criterion → command/result or explicit gap>
Limitations: <unverified checks, temporary breakage, recovery/live boundaries>
Review status: full phase implementation ready / pending fresh review, or slice complete / phase in progress
Review handoff for a complete numbered phase: Ali manually starts a new fresh review chat against this OPEN PR before merge:
Read planning/prompts/review.md and review open SKY-025 implementation/fix PR <this PR URL>.
Include earlier merged slice PRs/SHAs needed to judge the complete numbered phase.
```

For an intermediate slice, give an execution continuation for the remaining same-phase work, not an
independent review invocation. For a FIX, update the same open reviewed PR unless the reviewer explicitly
identifies a repository-state reason that makes that impossible. Return the PR URL and applicable
handoff, then stop. If publishing is unavailable, preserve the branch/commit and exact PR title/body and
report the access blocker.
