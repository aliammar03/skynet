---
date: 2026-09-10
time: 17:37:48            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 P2 replace worker roles and Codex configuration
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-026, SKY-022]
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-10 · session · SKY-026 P2 replace worker roles and Codex configuration

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Executed SKY-026 Phase 2: make native Codex config match the Phase-1 doctrine and erase the SKY-022
runtime surface. Based the branch `feat/sky-026-p2-worker-roles-codex-config` on `origin/main`
(which already carries Phase 1's six-role construction.md but still had builder/mechanic/scout TOMLs
and the cap). The open P1-fix branch (54a5ef3, docs-only) is independent of this runtime work, so I
did not stack on it.

Re-read the pinned donor source contracts (viettran-edgeAI/codex_workflow @ 6d9b06f) by fetching the
six worker TOMLs raw from GitHub: `codex_workflow/agents/{companion,investigator,default_executor,
senior_executor,tester,archivist}.toml`. Borrowed each worker's developer_instructions closely, then
adapted only the Skynet deltas: replaced every `agent_docs/` reference with Skynet's canonical
surfaces (the active directive, append-only journal, system-design/design spokes, generated context),
and added explicit production isolation + "never hand-edit `inventory/`/`docs/generated/`" to every
write role.

Verified model/effort/sandbox against the INSTALLED harness, not just the README:
- `codex-cli 0.153.4`; user `~/.codex/config.toml` runs `gpt-5.6-sol` medium.
- Ran real `codex exec` smoke tests: `gpt-5.6-luna` @ `xhigh` read-only → ran and replied; `gpt-5.6-luna`
  @ `max` workspace-write → ran. So the donor's xhigh/max/medium efforts and luna/sol IDs are all
  accepted by this harness. No substitution needed (source TOML wins).

Settled the concurrency-cap question empirically. `max_concurrent_threads_per_session` is a REAL codex
`[agents]` field, not a SKY-022 invention: setting any other scalar key under `[agents]` (e.g.
`agents.max_threads_per_session=2`) errors `invalid type: integer 2, expected struct AgentRoleToml`,
while `agents.max_concurrent_threads_per_session=2` loads cleanly. So the mechanism is platform-supported;
only the value `2` was SKY-022 doctrine. Per Decision I, removed the pinned setting entirely and let
codex's own default apply (the donor ships no cap). The invariant gate now FAILS if the key reappears.

## Actions & outcomes
- Added six `.codex/agents/*.toml` (companion, investigator, default_executor, senior_executor, tester,
  archivist) with model/effort/sandbox = luna·xhigh·ro, luna·xhigh·ro, luna·max·ww, sol·medium·ww,
  luna·xhigh·ww, luna·xhigh·ww → matches the doctrine table.
- `git rm` builder/mechanic/scout TOMLs → no legacy role definition remains.
- `.codex/config.toml`: removed `max_concurrent_threads_per_session = 2`; comment now states the
  no-workflow-quota model + semantic limits live in the doctrine.
- `invariants.json` construction block: dropped the cap, replaced the 3-agent list with the 6 roles +
  sandboxes, kept `forbidden_sandbox_mode: danger-full-access`.
- `scripts/check-invariants.sh` §6: removed the cap-equality check; now FAILS if the config pins a cap;
  kept the per-role declared-sandbox check and the danger-full-access scan.
- `bin/agent`: rewrote. Role set is exactly the six workers; each resolves model/effort/sandbox by
  READING its `.codex/agents/<role>.toml` (source TOML wins, launcher cannot drift). Dropped the
  SKY-022 `lead`/`review` roles, `--tier`, and the `AGENT_MODEL_*` tier overrides; kept `--cwd`
  worktree validation and `--dry-run`. Refuses danger-full-access.
- Rewrote `tests/agent-test.sh` (74/0) and `tests/construction-test.sh` (16/0) around the six roles,
  legacy-vocabulary rejection, and cap-absence; updated the `.githooks/pre-commit` comment lines.
- Gates green: check-invariants OK; agent-test 74/0; construction-test 16/0; secret-scan, entity,
  digest, provisioning-truth, dns-revert, compose-rollback, cert-selector, tofu-rollback, pve-snapshot,
  gitignore, nightly-automerge, nightly-sequence all OK.
- Kept every new runtime file free of `SKY-###` provenance (temporal-hygiene intent) — it points to
  `docs/conventions/construction.md` instead. The gate's remaining hits are pre-existing (Phase 1's
  construction.md/runbook, SKY-025's routes.py/collect-network-gear.sh), untouched here.

## Graveyard — tried & abandoned
- Considered keeping a thin `review`/`lead` launcher role for the fresh-session review — abandoned: the
  fresh acceptance review is just a fresh session with the selected model (doctrine), so no launcher
  role is needed, and keeping one would preserve SKY-022 vocabulary the supersession rule forbids.
- Tried to confirm codex's agent-discovery mechanism from the binary strings — abandoned: the wrapped
  ELF yielded nothing useful. Relied instead on the established, CI-green repo convention that
  `.codex/agents/*.toml` + `.codex/config.toml` is the discovery surface (proven since SKY-022 P2).

## Follow-ups / open threads
- Phase 3 dogfoods this runtime (Heavy route: Companion + Executor + Tester + capsules + batching +
  Executor↔Tester repair) to prove behavior changed, not just filenames.
- Token accounting (donor deployment-token-report) is deliberately NOT wired — Phase 4 owns it; the
  archivist TOML says so and forbids fabricated usage.
- Phase 5 owns the exhaustive SKY-022 sweep of the remaining current-authority surfaces (including the
  SKY-025 inline execution model and the two Phase-1 `SKY-026 role` mentions the temporal-hygiene gate
  still flags).
