# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; this file is updated by Main after acceptance or a paused/blocked closure.

## Detailed Current State

SKY-026 Phase 4 is accepted. The current bounded follow-up replaces Codex construction approval
checkpoints with the unprivileged `aliammar` Unix boundary: ordinary work is prompt-free, while
authored self-merge and self-root escalation are forbidden.

## Session Changes

- Home Manager now declares `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`.
- Project and role configs no longer impose workspace sandboxes; native children inherit the
  spawning session's unprivileged account posture.
- Exec policy hard-blocks `gh pr merge`, `bin/grant-root`, and `./bin/grant-root` with no prompt
  fallback. Trust tiers, credential permissions, and production authority are unchanged.
- Current construction doctrine and deterministic contract tests reflect the resulting rule; obsolete
  approval-churn workarounds are removed.

## Verification

- Home Manager evaluation resolves to approval `never`, `danger-full-access`, and exactly three
  forbidden exec-policy rules; installed Codex 0.153.4 classifies those commands as forbidden.
- Independent focused construction and permission checks pass, as do pytest, Ruff, mypy, Nix flake
  checks, pre-commit, and diff checks.
- Representative repository, Git, GitHub, Nix, and temporary-directory actions execute as
  `aliammar`; source/configuration checks cover `.agents/` and `.codex/`. Secret modes remain
  restrictive and no root was acquired.

## Pending Work and Blockers

- The checked-in Home Manager target is not activated in the current shell, whose installed user
  configuration still reports `OnRequest`; activation must follow human merge.
- A nested installed-CLI child probe hit a runtime thread error and then the account usage limit.
  Source contracts prove that roles do not override the spawning posture, but a fresh
  post-activation child smoke test is still required to observe target-profile inheritance.
- The enclosing pre-merge managed session exposes `.agents/` and `.codex/` read-only, so direct
  write probes there cannot demonstrate the undeployed target from this session.

## Next Entry Point

Human-merge this bounded permission PR, activate its Home Manager generation through the normal
declarative path, and smoke-test one native child. Then continue
[`planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md`](../planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md)
at Phase 5; treat SKY-022 only as historical provenance.
