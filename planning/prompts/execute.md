---
summary: "Execute one authorized SKY-025 phase or fix packet and publish its evidence in a GitHub PR."
---

# Execute one packet

> Execution prompt for the [phase handoff workflow](README.md). Follow the active SKY-025 directive.

Execute the next authorized SKY-025 packet, or the phase/slice specified by Ali.

1. Read AGENTS.md and planning/README.md. Locate the single active SKY-025 directive by ID
   (`bin/plan show SKY-025`, or tracked files if that helper has been replaced). Read its current
   packet, disposition map if present, and relevant conventions. Load other files only as needed.
2. Resolve current remote main and start a clean branch from it; preserve unrelated local work.
   Record the base SHA. Verify the phase authorization is merged, its preceding numbered phase accepted, and
   there is no outstanding FIX/BLOCKED review. A merged FIX packet authorizes only those fixes.
   Phase 1 is the bootstrap exception: its merged detailed packet needs no predecessor review.
   If an implementation PR already exists for this packet, inspect/reuse it rather than duplicating it.
   For remaining slices within the authorized phase, the execution lead details the next bounded
   packet before work. Completed slices need no independent review; preserve human merge and
   live/grant prerequisites. Never advance to the next numbered phase without phase acceptance.
3. Confirm the session's model/effort matches the packet. Follow the directive's routing rules;
   do not claim a model switch or silently substitute an unavailable model. Use at most two scoped
   Luna workers where worthwhile, with the directive's worker packet and restrictions.
4. Implement only this 1–2h packet, including affected callers, tests, and current documentation.
   Follow its live boundaries and existing authorization. Downtime tolerance does not expand data,
   credential, or privilege authority. If the scope no longer fits, propose a bounded slice and
   record unfinished exits; do not quietly expand scope or declare the phase complete.
5. Inspect worker changes and run the packet's meaningful checks. Report exact commands, results,
   skipped/unavailable checks, and temporary breakage. Do not invent validation or weaken an exit
   criterion. Resolve concrete defects within scope; escalate unresolved architecture/recovery
   decisions according to the directive.
6. Record close-out evidence as the directive requires. Record slice and full-phase status separately;
   do not increment accepted progress, accept your own phase, or flesh out dependent numbered phases.
   Mark a completed slice as phase-in-progress; review-pending applies only when all phase slices finish.
   Commit and push the scoped changes and open an authored PR to main. Never merge it.

Use this PR title: `SKY-025 P<N>: <outcome>` (or `SKY-025 P<N> fix: <outcome>`).
Use these compact PR body fields; replace placeholders with evidence:

```text
Packet: <phase/slice; merged planning PR or bootstrap directive commit>
Base: <full main SHA>
Why and changes: <problem, implemented behavior, affected callers/docs>
Exit evidence: <each criterion → command/result or explicit gap>
Limitations: <unverified checks, temporary breakage, recovery/live boundaries>
Review status: full phase complete / review pending, or slice complete / phase in progress (or incomplete; remaining exits)
Handoff for a complete numbered phase: after Ali merges all phase PRs, start a fresh Astra Medium task:
Read planning/prompts/review.md and review SKY-025 implementation PR <this PR URL>.
For fixes, also review original implementation PR <URL> and earlier fix PRs <URLs>.
```

For an intermediate slice, give an execution continuation for the remaining same-phase work,
not an independent review invocation. Return the PR URL and applicable handoff. Stop at this packet. If publishing is
unavailable, preserve the branch/commit and exact PR title/body and report the access blocker.
