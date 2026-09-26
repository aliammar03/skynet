---
summary: "Fresh-session review of one PR: verify the tier, run bin/check, check exit evidence, post one verdict comment."
---

# Review a PR

You did not author this change. Do not edit the branch.

1. Read `AGENTS.md`, the PR description and diff, and the directive phase it claims.
2. **Tier.** Confirm the claimed tier against the Full list in
   [`construction.md`](../../docs/conventions/construction.md). A Light claim on Full work is a FIX.
3. **Checks.** Check out the PR head and run `bin/check`. It must pass.
4. **Substance.** Does the change meet the phase's exit evidence? For a write path: is there a
   failure-case test that exercises the rollback or refusal? Does anything widen authority, weaken a
   gate, or leave a caller pointing at a deleted path? Is the directive status updated truthfully?
5. **Verdict.** Post exactly one PR comment: findings, then a paste-ready fix list for the authoring
   session, ending with `Verdict: ACCEPT` or `Verdict: FIX`. A new push needs a new review.
