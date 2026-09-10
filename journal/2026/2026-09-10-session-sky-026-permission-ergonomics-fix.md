---
date: 2026-09-10
time: 22:58:15
kind: session
title: SKY-026 permission ergonomics fix
tier_touched: [T1]
grants: []
refs: [SKY-026, PR-251]
thread_status: open
---

# 2026-09-10 · session · SKY-026 permission ergonomics fix

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened

Ali accepted SKY-026 Phase 4 and requested one follow-up from current `main` to eliminate Codex
approval prompts during normal construction. Main updated Home Manager from `approval_policy =
"on-request"` to `"never"`, retained the existing `danger-full-access` user sandbox, and changed the
three exec-policy rules for `gh pr merge`, `bin/grant-root`, and `./bin/grant-root` from `prompt` to
`forbidden`. The project `workspace-write` override and all six role-level sandbox overrides were
removed. No T2/T3 operation, credential, root grant, live host, or production actuator was used.

Current doctrine and tests were changed to make the unprivileged `aliammar` NixOS account the
filesystem/OS construction boundary. The old project sandbox and TMP-specific permission-noise
guidance were removed from current surfaces. Trust tiers, human merge, secret handling, and
production authority contracts were left intact.

## Actions & outcomes

- `nix eval` of the Home Manager Codex module → target settings were `approval_policy=never` and
  `sandbox_mode=danger-full-access`; all three rules evaluated to `forbidden`.
- Installed Codex 0.153.4 `execpolicy check` against the evaluated rule source → all three prohibited
  commands returned `decision:"forbidden"`; representative Git, GitHub, Nix, and temporary commands
  had no blocking rule.
- An ephemeral installed-Codex run with the target permission profile → reported `approval: never`,
  `sandbox: danger-full-access`, ran as `aliammar`, edited/staged/cleaned a repository probe, switched
  the current branch, read a harmless GitHub PR, entered the Nix development shell, and completed
  without an approval interaction.
- Independent Tester verification → permission tests, 41 construction checks, invariants,
  274 pytest tests, Ruff, mypy, Nix flake checks, pre-commit, and diff checks passed; the unrelated
  untracked `inventory/tofu-drift.txt` remained untouched.
- `stat -L` on the Cloudflare materialized secret → mode `0400 aliammar:users`; the lab age key was
  mode `0640` with group `users`. Secret contents were not read. `id` reported uid 1000 `aliammar`,
  and `sudo -n true` did not yield root.

## Graveyard — tried & abandoned

- The project `workspace-write` boundary and role sandbox declarations were removed because they
  converted ordinary unprivileged construction into approval churn without defining production
  authority.
- TMP-only test advice was removed where its sole purpose was avoiding sandbox prompts; canonical
  tests, maintained fixtures, and language-native temporary cleanup remain current practice.
- The first ephemeral nested Codex child spawn returned `collab spawn failed: no thread with id ...`.
  A non-ephemeral retry reached the installed account usage limit before spawning, so no further
  nested-CLI retries were made.
- A direct `.agents/`/`.codex/` write probe in the enclosing pre-merge managed session failed with
  `Read-only file system`. That session carries the old managed permission profile, so it cannot
  demonstrate the undeployed target; the created `/tmp/sky026-permission.HnOJ92` probe was removed.
- The first final `nix develop` suite tried to update
  `/home/aliammar/.cache/nix/fetcher-cache-v4.sqlite` and failed `attempt to write a readonly
  database` under the enclosing profile. Re-running the same pytest/Ruff/mypy commands with a fresh
  `/tmp/sky026-nix-cache.*` as `XDG_CACHE_HOME` passed, and that cache was removed.
- PR #251's first remote Python job failed because GitHub's generic Nix development shell does not
  install the target-only `codex` binary. The installed-policy test was changed to skip only when
  `codex` is absent; it continues to run on `vm-skynet-ops`, while the portable source/configuration
  tests still run in CI.

## Follow-ups / open threads

- The current installed Home Manager generation still reports `approval OnRequest`; the authored
  target must be human-merged and activated through the normal declarative path before the live user
  configuration changes.
- After activation, run one fresh native-child smoke test, then continue SKY-026 Phase 5.
- After activation, directly write and remove harmless probes in `.agents/` and `.codex/`; the
  current pre-merge session could verify their configuration contracts but not their live writes.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
