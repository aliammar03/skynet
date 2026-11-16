---
status: accepted
date: 2026-11-15
decision-makers: Ali
---

# One layout, and work tracked as issues, plans and records

## Context and Problem Statement

The build is over. Its plan, one Markdown file at the repo's root, had grown to 2,650 lines: the
status, the decisions, the conventions, the lab's facts and every phase's steps in one file. An agent should find each
kind of thing by its path, and new work needs a fixed route from idea to done, with no phases.

## Considered Options

Established conventions, one per kind of thing:
- decisions: [MADR 4.0](https://adr.github.io/madr/);
- the agent's contract: [AGENTS.md](https://agents.md/), one root file, the folder contracts as
  READMEs that any tool and any reader finds;
- Nix: the flake folders most configs use and
  [blueprint](https://numtide.github.io/blueprint/main/getting-started/folder_structure) names
  (`hosts/`, `modules/`, `packages/`), the names only, not the library;
- secrets: `<what>.sops.<ext>`, beside what reads it;
- the backlog: GitHub Issues;
- titles: `<area>: <sentence>`, as nixpkgs and the kernel do.

## Decision Outcome

Chosen option: those conventions, and:
- The build's plan is deleted once every still-true fact has a home. Git keeps the build's steps;
  `README.md` names the last commit with the file.
- A machine is one folder (`hosts/<name>/`, for every machine git configures, NixOS or not, its
  secrets beside it), a stack is one folder, a decision is one file (`docs/decisions/`), a
  procedure is one file (`runbooks/`), and a project in flight is one file (`docs/plans/<slug>.md`):
  the agent PRs the plan, Ali's merge approves it, and its closing PR deletes it, leaving the truth
  in READMEs and records.
- An idea kept for later is a GitHub issue, one each.
- A changed decision is a new record that supersedes the old one.
- Comics and the arena stay as stacks; the platform's docs stop describing them, and each keeps its
  README.
- Ali's review as code owner guards `docs/decisions/` and `docs/plans/`, beside what it guarded
  already: the root `AGENTS.md` and `CLAUDE.md`, `.claude/`, `.mcp.json`, `.github/`, and the gates
  and aliases the autonomy plan adds. Reference pages, READMEs and runbooks are the agent's to keep
  current.
- The Glue budget goes. Mature tools stay first (`AGENTS.md`, rule 6), and a new program of our
  own needs a decision record naming the mature tools it ruled out.
- A branch is `<area>/<slug>` and a PR's title `<area>: <sentence>`; the area is the plan's slug,
  else the stack, host or top folder.

### Consequences

- Good, because each kind of thing has one home, and `AGENTS.md`'s map reaches it in one hop.
- Good, because a plan's merge is its approval, and a decision's history is in its own file.
- Bad, because old paths and links break once: `README.md` names the last commit that had the
  plan, and git keeps every move as a rename.

## More Information

Ali's answers, 2026-11-15, recorded in the restructure plan (#199, merged 2026-11-16).
