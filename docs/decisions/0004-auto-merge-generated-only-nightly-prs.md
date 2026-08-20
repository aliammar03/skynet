# ADR 0004 — Auto-merge generated-only nightly PRs

- **Status:** accepted
- **Date:** 2026-08-20

## Context

The deterministic nightly (`scripts/nightly.sh`) opens a PR every night whose diff is purely
mechanical: refreshed `inventory/`, re-rendered `docs/generated/`, a raw `journal/` episode, and any
re-encrypted `compose/*/.env.sops`. Nothing in it is *authored* — no human or LLM reasoned about the
content; it is a snapshot of observed truth plus regenerated views. Under the standing "human merges
every PR" gate, these accumulated as an un-drained backlog (e.g. #89 on top of earlier ones). A
merge queue nobody empties is not a safety control — it is latency that trains everyone to rubber-stamp,
which is worse than an honest auto-merge.

The constitution already anticipated this exact step. `docs/system-design.md` §2b records the merge
gate as a *version-controlled dial*, not an absolute, and names its **foreseeable first loosening**:
"the agent auto-merging docs-only PRs." This ADR takes that step, widened slightly from "docs-only"
to "generated-only" so it also covers the encrypted env layer the same nightly produces.

Constraints that shape the decision:

- **Never self-merge authored change.** The "agent never merges its own PR" invariant exists to stop
  a buggy or compromised agent pushing reasoned changes (code, compose, routes, design) to `main`
  unreviewed. That protection must survive intact; only the mechanical class is exempted.
- **No server-side backstop.** The repo is private on a free GitHub plan, where branch-protection
  rulesets are **not enforced**. Upgrading (Pro/Team) or going public were both rejected — the repo
  carries lab topology and sops blobs and is correctly private. So the gate has to live in our code,
  not GitHub's.
- **CI already runs the hard gates on every PR** (`.github/workflows/checks.yml`: budget-frontmatter,
  secret-scan, check-invariants) — the same deterministic checks as the pre-commit hook.

## Decision

The nightly may **self-merge the PR it just opened**, but only when *both* hold:

1. **Path allowlist** — every changed path is under `inventory/`, `docs/generated/`, `journal/`, or
   matches `compose/*/.env.sops` (encrypted env). One path outside → the PR is left open for a human.
2. **Green CI** — `gh pr checks --watch` blocks until every check completes and passes; a red or
   never-arriving check → left open.

Enforced in `scripts/nightly.sh` (`automerge()`), guarded by `OPS_NIGHTLY_AUTOMERGE` (default on;
`=0` disables without a code change or revert). The dial position moves in `docs/system-design.md`
§2b and the change is registered as the first entry on the `AGENTS.md` §3 auto-approve list.

Everything **authored** — design, code, compose, runbooks, ingress/publish rules — stays
human-merged, unchanged.

## Consequences

- The nightly backlog drains itself; a generated snapshot lands on `main` within minutes of a green
  CI run, so `inventory/` and `docs/generated/` track reality without a human in the loop for content
  they never edit anyway.
- The safety property is **code, not trust**: the allowlist is a literal path filter and the green-gate
  is `gh pr checks`' own exit status. A regression in either fails *closed* (PR stays open) — the pre-change
  behaviour — never open (an unreviewed authored merge).
- Because there is no branch protection, the green-gate is the *only* thing standing between the nightly
  and `main`. If CI is ever misconfigured to pass vacuously, this path would merge on a false green.
  Mitigation: the same checks gate the pre-commit hook and every human PR, so a vacuous-pass CI is a
  lab-wide problem we would notice, not one unique to auto-merge.
- A human can still hand-push a broken commit to `main` (nothing blocks it), but CI runs on push and
  flags it red. That risk is unchanged by this ADR.
- `OPS_NIGHTLY_AUTOMERGE=0` is the instant off-switch; `git revert` of the enabling PR is the durable
  one. The leash stays in git.
