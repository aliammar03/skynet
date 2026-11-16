---
status: accepted
date: 2026-10-21
decision-makers: Ali
---

# The repo is public, the lab pulls, and CI is static checks

## Context and Problem Statement

The hosts need to read their config without a credential, and `main` needs a ruleset and code
owners. GitHub Free offers rulesets and CODEOWNERS only on public repositories.

## Decision Outcome

Chosen option: the repository `aliammar03/skynet` is **public**; the lab **pulls** it (comin,
doco-cd) and nothing outside pushes in; CI is static checks on GitHub's free runners
(`.github/workflows/check.yml`), because that gives the ruleset and code owners on GitHub Free with
nothing inbound.

### Consequences

- Good, because nothing outside the lab can reach into it, CI included.
- Bad, because everything in git is public: secrets are sops files only, and no secret value goes
  into a file, an issue or a PR (`runbooks/survival-kit.md`).
- Bad, because CI can't reach the lab, so checks that need it run on ops.

## More Information

Ali, 2026-10-21, at the start.
