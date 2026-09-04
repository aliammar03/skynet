---
date: 2026-09-04
kind: session
title: Codex permissions match Claude on NixOS
tier_touched: [T1]
grants: []
refs: ["PR (fix/codex-permissions-match-claude)", nix/home/aliammar.nix, nix/README.md]
---

# 2026-09-04 · session · Codex permissions match Claude on NixOS

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used. -->

## What happened

Ali reported that Codex asked permission for nearly every command, called out Nix commands
specifically, and asked that opening PRs remain prompt-free. The Nix-managed Claude configuration
already used `acceptEdits` plus an all-Bash allow, with asks only for `gh pr merge` and the two
`grant-root` command forms. Codex instead used `approval_policy = "on-failure"` and
`sandbox_mode = "workspace-write"`; Git metadata and other user-owned paths therefore crossed its
sandbox boundary even though the `aliammar` OS account was already the intended security wall.

Changed the Home Manager Codex configuration to `danger-full-access` for the interactive lead and
`on-request` for the explicit rule checkpoints. Added managed `skynet.rules` prompt rules for
`gh pr merge`, `bin/grant-root`, and `./bin/grant-root`. The named rules file avoids colliding with
the existing unmanaged `~/.codex/rules/default.rules` that Codex writes for remembered approvals.
No allow rules were added for ordinary commands: with the interactive sandbox removed, Nix, local
edits, Git work, branch pushes, and `gh pr create` run directly as the unprivileged OS user.

Ali also requested Sol medium as the default. Added `model = "gpt-5.6-sol"` and
`model_reasoning_effort = "medium"` to the same Home Manager settings. SKY-022 helpers keep their
separate role models and sandboxes because `bin/agent` passes explicit command-line overrides.

## Actions & outcomes

- Read the current official Codex configuration/rules references: `on-failure` is deprecated;
  `on-request` and `never` are current, and prefix rules support allow/prompt/forbidden decisions.
- Evaluated the pinned Home Manager Codex module; confirmed it supports declarative `.rules` files.
- `nix eval` rendered Sol medium, on-request, danger-full-access, the trusted Skynet project, and
  all three prompt prefixes.
- `nix flake check --no-write-lock-file` passed all checks and built the Home Manager generation.
- `codex execpolicy check` returned `prompt` for `gh pr merge` and `./bin/grant-root`; `gh pr create`
  and `nix flake check` matched no prompt rule.

## Graveyard — tried & abandoned

- Keeping `workspace-write` and adding an ever-growing allowlist was rejected. It would reproduce
  the prompt churn command by command and drift from Claude's existing all-Bash posture.
- Managing `default.rules` through Home Manager was rejected because a real local file already
  exists there and Codex owns that filename for remembered interactive approvals.

## Follow-ups / open threads

- Human-merge the PR, then switch `vm-skynet-ops` through the normal reviewed NixOS deployment path.
  New Codex sessions will pick up the generated config and `skynet.rules`; this running session does
  not reload them.
