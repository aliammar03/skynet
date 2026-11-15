---
status: accepted
date: 2026-11-15
decision-makers: Ali
---

# The bot has Write; `main` takes a PR with CI green, and Ali's review on what he owns

## Context and Problem Statement

The agent's account has to push branches and open PRs in the one repository, and `main` must take
only changes that passed CI. Ali's review has to guard what bounds the agent without a click on
every PR.

## Decision Outcome

Chosen option: `aliammar-skynet` has **Write**. The `main` ruleset requires a PR and the check
`nix`, requires Ali's review as code owner for the paths in `.github/CODEOWNERS` (stale approvals
dismissed on new commits), and blocks force-push and deletion. Nothing else requires a review.
Because branches live in one repository, and the only approval clicks are the code owner's.

### Consequences

- Good, because code-owner review is a hard wall for the contract, the gates, the plans and the
  decisions.
- Bad, because "never merge" is a soft wall everywhere else: `AGENTS.md` and Claude Code's deny
  rules. The bot's token could merge a PR that touches no code owner's file.

## More Information

Ali, 2026-10-21: Write, and no required review. 2026-11-09: code-owner review, with the autonomy
plan's leash; turned on 2026-11-15 (#185). The plan for the agent to merge through gates, by what
a rollback can undo, is `docs/plans/autonomy.md` → Merges. Until it goes live, Ali merges every PR.
