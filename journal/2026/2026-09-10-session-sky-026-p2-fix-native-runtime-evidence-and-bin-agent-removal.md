---
date: 2026-09-10
time: 18:20:00            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 P2-fix native-runtime evidence and bin/agent removal
tier_touched: [T1]
grants: []
refs: [SKY-026]
thread_status: none
---

# 2026-09-10 · session · SKY-026 P2-fix native-runtime evidence and bin/agent removal

<!-- RAW EPISODE. Append-only. This does NOT replace the Phase 2 episode
     (2026-09-10-session-sky-026-p2-replace-worker-roles-and-codex-configuration.md); it records the
     fixes to the three independent-review findings on merged PR #244 (186449e). -->

## What happened
Independent review of PR #244 raised three findings: (1) `bin/agent` was a false "native mirror" —
it set only model/effort/sandbox and never loaded a role's `developer_instructions`, so `bin/agent
companion` was a Luna/read-only preset, not a Companion; (2) Phase 2 never proved native in-session
discovery/spawn of the six roles (it relied on generic `codex exec` smokes and on superseded SKY-022
evidence); (3) the generated roadmap in `planning/README.md` still showed SKY-026 `0/5`.

### Native mechanism, verified from source (openai/codex rust-v0.153.4)
- `codex-rs/agent-roles/src/discovery.rs` + `loader.rs`: Codex discovers one role per `*.toml` under
  each config layer's `agents/` dir (recursive, description required). So project `.codex/agents/*.toml`
  are discovered as a config layer.
- `codex-rs/core/src/agent/role.rs` `apply_role_to_config`: looks up `role_name` in the discovered
  `config.agent_roles`; unknown → error `unknown agent_type '<name>'`. It applies the role's
  `developer_instructions`, `model`, `model_reasoning_effort` (and layers the full role TOML via
  `build_config_layer_stack`).
- `codex exec --help`: NO `--agent`/`--role` flag anywhere (checked exec, resume, fork, review, cloud,
  top-level). Spawning is the in-session `spawn_agent` tool (namespace `multi_agent_v1`,
  `agent_type=<role>`), from `core/src/tools/handlers/multi_agents/spawn.rs`.
- `codex features list`: `multi_agent` is `stable` and `true` (enabled by default).
Conclusion: there is NO supported standalone CLI that invokes a named role and loads its full contract.
A shell wrapper cannot mirror the native loader. Per the review's YAGNI outcome → delete `bin/agent`.

### Installed-harness native smoke (the evidence Phase 2 lacked)
Run 1 — parent `codex exec --sandbox workspace-write -C . --model gpt-5.6-sol` (session
`01a08b69-1fec…`): Main called `spawn_agent` once per role, in order, for all six
(companion, investigator, default_executor, senior_executor, tester, archivist). Every call RESOLVED —
each returned `{"task_name":"/root/discovery_<role>"}`; **zero** `unknown agent_type` errors. Per-child
rollout evidence:
- each child's `agent_role` = the intended role name (all six);
- each child carries **its own** role file's `developer_instructions` verbatim (grepped a role-unique
  phrase in each of the six child rollouts: "You are Companion", "You are Investigator", "You are
  `default_executor`", "You are `senior_executor`", "independent verification engineer", "You are
  Archivist") → the native loader loads the COMPLETE role contract, not a preset;
- `thread_settings_applied` shows the per-role **model override** applied: luna for
  companion/investigator/default_executor/tester/archivist, sol for senior_executor — matching each
  role file, overriding the parent's sol.

Run 2 — parent `--sandbox read-only` (session `01a08b6e-1a36…`): spawned companion (read-only role) +
default_executor (workspace-write role). Both resolved; both children's `thread_settings_applied`
filesystem access was `restricted` (read-only).

### Sandbox reality (honest characterization)
The child's filesystem sandbox is the **spawning session's sandbox as a ceiling**: a role never
escalates above it (default_executor ran read-only under a read-only parent), and in 0.153.4 the role
file's own `sandbox_mode` does NOT by itself reduce a worker below a workspace-write parent — in run 1,
companion (declared read-only) ran with workspace write because the parent was workspace-write. So a
read-only role's no-write guarantee holds only when Main spawns it from a suitably bounded session.
Corrected the overclaim accordingly: construction.md "Trust and native tooling" and the invariants.json
construction `why` now state that the gate enforces the DECLARED sandbox (least-privilege intent) while
runtime reach is parent-bounded, and that the always-true boundary is zero production authority
(no credential/token/root/T2/T3 reaches any worker regardless of sandbox). The gate and the six
declared sandboxes are unchanged.

## Actions & outcomes
- `git rm bin/agent tests/agent-test.sh` → native Codex spawning is the sole worker mechanism.
- Updated current-authority references off `bin/agent`: `docs/conventions/construction.md`
  (native-only, no launcher), `runbooks/construction-delegation.md` (frontmatter + step 5),
  `planning/sky-025-map.md` (row now records the launcher's removal), `.githooks/pre-commit`, and
  `.github/workflows/checks.yml` (dropped the `agent-test` step + comments). Journal/archive
  references left untouched (append-only history).
- Rewrote `tests/construction-test.sh` to validate the REAL role source files (python `tomllib`): each
  of the six parses, `name` matches filename + unique, model/effort/sandbox/description/
  developer_instructions present and non-empty, sandbox == invariants.json, none danger-full-access;
  legacy scout/mechanic/builder absent; no concurrency cap pinned; drift fixtures rejected. 23/0.
- Regenerated `planning/README.md` with `bin/plan list` (the owning tool, not by hand): SKY-026 now
  `2/5` (the regen also corrected stale horizon columns for SKY-010/011/024). Re-running produces no
  further diff.
- Corrected the sandbox-enforcement overclaim in construction.md + invariants.json (above).
- Gates: check-invariants OK; construction-test 23/0; entity/digest/dns-revert/compose-rollback/
  cert-selector/tofu-rollback/pve-snapshot/provisioning-truth/gitignore/nightly-automerge/
  nightly-sequence all OK; `git diff --check` clean.

Current SKY-026 construction runtime behavior is now established ENTIRELY from installed-Codex native
evidence (source + the two live smokes above). It does not depend on SKY-022 in any way; SKY-022
remains inert archive/journal history only.

## Graveyard — tried & abandoned
- Keeping `bin/agent` as a "thin standalone/debug launcher" → abandoned: it cannot load a role's
  developer_instructions or invoke the named role, so it is a misleading non-role. No supported CLI
  replacement exists; native in-session spawn is the only faithful mechanism.
- Reading the installed codex ELF via `strings` to confirm discovery → abandoned (stripped/empty).
  Used the pinned rust-v0.153.4 source + live rollout evidence instead.

## Follow-ups / open threads
- SKY-026 stays `current_phase: 2`; Phase 3 stays unreleased until this fix merges and a fresh review
  re-accepts. Phase 3 dogfoods the Heavy route on real work.
- 0.153.4 does not reduce a worker's sandbox below a workspace-write parent from the role file alone.
  If a future requirement needs mechanical read-only for a role regardless of parent, investigate
  whether a `permission_profile` in the role layer (vs bare `sandbox_mode`) reduces it, or spawn
  read-only roles from a read-only Main. Not required for SKY-026 safety (zero production authority is
  the real boundary).
