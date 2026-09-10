---
date: 2026-09-10
time: 19:05:00
kind: session
title: SKY-026 P2-fix2 construction session sandbox boundary
tier_touched: [T1]
grants: []
refs: [SKY-026]
thread_status: none
---

# 2026-09-10 · session · SKY-026 P2-fix2 construction session sandbox boundary

<!-- RAW EPISODE. Append-only. Does NOT replace the prior P2 / P2-fix episodes. Records the second
     independent re-review's platform finding and the permission model chosen. -->

## What happened
Second independent Phase-2 re-review (after PRs #244, #245) accepted the first three findings but
flagged one platform defect plus stale surfaces: the Phase 2 exit criterion "read-only roles cannot
write" is false on Codex 0.153.4, and the user config's `danger-full-access` default meant native
construction workers could inherit it (bin/agent, which used to pass `--sandbox`, is gone).

### Platform truth (confirmed against openai/codex rust-v0.153.4 + installed 0.153.4)
- `core/src/agent/role.rs` `AgentRoleOverrides` applies a role file's developer_instructions, model,
  reasoning, service tier, feature disables, skills — NOT `sandbox_mode`.
- `tools/handlers/multi_agents_common.rs` `apply_spawn_agent_runtime_overrides` copies the spawning
  turn's permission profile into the child; `spawn_agent` has no child-sandbox argument.
  → A native worker's filesystem leash is the SPAWNING SESSION's permission profile, not its role file.
- `config/src/loader/README.md` precedence (top wins): SessionFlags > **Project `.codex/config.toml`** >
  user profile > **user `config.toml`** > enterprise > system. So a project-level sandbox overrides the
  user-level `danger-full-access`.

### Evidence on the installed harness
- BEFORE: a normal project session (no flags) reported `sandbox: danger-full-access` (session
  `01a08b93`, no agent_role — standalone). That is what workers would have inherited. The defect was real.
- Set project `.codex/config.toml`: `sandbox_mode = "workspace-write"` + `[sandbox_workspace_write]
  network_access = true`.
- AFTER: a normal project session reported `sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network
  access enabled)` — the project layer wins over the user `danger-full-access`.
- Native smoke from the NORMAL config (parent session `01a08b95`, no `--sandbox` flag, reported
  workspace-write): spawned companion, investigator, default_executor, tester — all four resolved and
  each child's applied permission profile was `managed/restricted` (workspace-write), **none
  danger-full-access**; per-role model override still applied (luna). So construction workers now
  inherit the workspace-write ceiling, never danger-full-access.

## Actions & outcomes
- `.codex/config.toml`: set the construction session boundary (`sandbox_mode = "workspace-write"`,
  network on) with a comment explaining the role-file-sandbox-not-applied platform fact and the
  project>user precedence.
- `nix/home/aliammar.nix`: removed the false "Helpers remain bounded because bin/agent passes an
  explicit per-role --sandbox" comment; now states the project layer overrides the user
  danger-full-access inside the repo and that workers inherit that ceiling.
- `.codex/agents/companion.toml` + `investigator.toml`: replaced the "no-write contract is mechanical"
  sandbox comment and the "read-only sandbox is the boundary" line with honest wording — read-only by
  ownership/instructions; `sandbox_mode="read-only"` retained as least-privilege intent.
- `docs/conventions/construction.md`: role table column → "Sandbox (declared)"; Companion/Investigator
  "read-only by ownership and instructions"; Trust-and-native-tooling paragraph now states the session
  sandbox (`.codex/config.toml` workspace-write) is the real leash and no worker inherits
  danger-full-access.
- `runbooks/construction-delegation.md`: tier line + step 5 describe session-derived sandbox and the
  workspace-write boundary; role exposure verifies model+effort (not sandbox).
- Directive Phase 2 exit criteria: replaced "read-only roles cannot write" with the achievable set
  (read-only by ownership/intent; session sandbox bounds filesystem reach; no worker inherits
  danger-full-access; zero production authority) + a platform note. `current_phase` stays 2.
- `invariants.json` + `scripts/check-invariants.sh`: the gate now asserts `.codex/config.toml`
  `sandbox_mode == workspace-write` and never `danger-full-access` (new `project_config` /
  `project_sandbox_mode`). `tests/construction-test.sh` asserts the same + a danger-full-access-config
  drift fixture. construction-test 26/0; check-invariants OK.

No launcher/proxy/second transport was built (YAGNI). Native Codex orchestration is unchanged; only the
session permission boundary and the honest wording changed.

## Graveyard — tried & abandoned
- Recreating per-role read-only via a custom launcher / nested read-only proxy agent → explicitly
  out of scope and rejected by the review; the session-level sandbox is the supported boundary.
- Removing the user-level `danger-full-access` entirely → unnecessary and out of scope: the project
  layer overrides it inside the repo, which is the construction boundary the review asked for.

## Follow-ups / open threads
- Remaining platform limitation: Codex 0.153.4 cannot mechanically reduce a single read-only role below
  a workspace-write session. If a future Codex applies role `sandbox_mode` (or `permission_profile`) per
  child, the Companion/Investigator declarations become runtime-enforced with no further change.
- Phase 3 stays unreleased until this fix merges and a fresh independent review re-accepts Phase 2.
