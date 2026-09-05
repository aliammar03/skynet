---
summary: "How change enters the repo: one branch per unit of work, one PR per phase, and the agent never merging its own PRs."
---

# Spoke · Git & pull requests

> How change enters the repo: one branch per unit of work, one PR per phase, and a merge gate the
> agent never operates on its own PRs. Governed by [`../conventions.md`](../conventions.md).

Tags: **[testable]** = a lint/CI gate could assert it; **[manual]** = holds by review.

## Branching

- **Never commit to `main` directly.** `[testable]` `main` is merge-only.
- **One branch per unit of work** `[testable]`, named by grammar:
  - `phase/<name>` — a directive phase
  - `deploy/<svc>` — a service deploy/update
  - `fix/<thing>` — a bug fix
  - `inventory/<date>` — a collector/inventory refresh
  - `plan/<slug>` — planning-only changes (directives, roadmap)
- **One PR per phase / per change** `[manual]`. Don't bundle unrelated work.

## Pull requests

- **PRs teach** `[manual]`: the description says *what* changed, *why*, and *what merging causes*.
  Ali is learning git/infra through these — write them as lessons, not changelogs.
- **Authored PRs are human-merged.** `[manual]` The deterministic nightly gate alone may merge its
  own generated-only, CI-green PR; all other changes wait for Ali. This is the invariant in
  [`AGENTS.md`](../../AGENTS.md) §6.
- **`git revert` is the rollback** `[manual]` — never force-push `main`, never rewrite shared
  history. Arcane and the inventory converge back after a revert.

## Commit messages

- **Conventional-ish subject prefixes** `[testable]`: `scaffold:`, `deploy:`, `fix:`,
  `inventory:`, `docs:`, `plan:`. Subject in the imperative, scoped where useful
  (`deploy(silly): …`).
- End agent-authored commits with the required `Co-Authored-By` trailer (per harness policy).
  `[manual]`

## What never gets committed

- **Plaintext secrets** — `.env`, `compose/*/.env`, `project.env`, `*.key`, `*.pem`, age keys.
  `[testable]` Enforced by `.gitignore` + the `.githooks/pre-commit` → `scripts/secret-scan.sh`
  gate. Only `*.env.sops` (encrypted) belongs in git. Full secret rules: the invariants block in
  [`../conventions.md`](../conventions.md) and [`../design/secrets.md`](../design/secrets.md).
- **Hand-edits to generated dirs** — `inventory/**`, `docs/generated/**`. `[testable]` Edit the
  collector/renderer, never the output. See [`layout.md`](layout.md).
