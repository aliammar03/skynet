---
summary: "Phase-specific execution leads, model-agnostic independent review, and at most two bounded Luna workers."
---

# Spoke · Construction delegation

> One accountable lead integrates bounded workers and owns the authored PR.
> Governed by [`../conventions.md`](../conventions.md); production authority stays with the trust tiers.

Tags: **[testable]** = a deterministic gate can assert it; **[manual]** = requires review.

## Execution and review

The active directive's authorized packet selects the execution lead and effort. `[manual]`

| Work | Model | Effort | Responsibility |
|---|---|---|---|
| Foundational design, consequential policy or recovery | `gpt-6-astra` | medium | Execution lead |
| Bounded implementation | `gpt-5.6-terra` | high | Default execution lead |
| Defined rendering/documentation passes | `gpt-5.6-sol` | low | Execution lead |
| Independent merged-result review and next packet | Operator-selected | Operator-selected | Fresh review session |
| Builder or mechanic | `gpt-5.6-luna` | high | Scoped implementation worker |
| Scout | `gpt-5.6-luna` | medium | Read-only inspection worker |

Verify exact identifiers and supported efforts in the installed harness. Do not guess identifiers or
silently substitute models. If unavailable, report routing blocked and ask Ali to select an available
identifier or update the harness. `[manual]` Model routing does not switch the invoking session.

Terra/Sol leads refer unresolved architecture, privilege, or recovery decisions to Astra Medium.
The lead owns decomposition, integration, verification, and PRs. A worker reports only its scoped
result. Merged-result review runs in a **fresh session**, never as the implementing lead's helper.
The reviewer may repair bounded defects directly, using Luna workers for scoped implementation,
tests and repetitive work. The reviewer inspects those changes, rechecks the affected full-phase
exits, and may accept the repaired phase in the same review PR. Human merge makes the repairs,
acceptance and next packet effective; those verified repairs need no additional review session.
Unresolved defects receive a bounded fix packet; missing evidence or decisions may block review.
The implementing lead still cannot accept its own phase. `[manual]`

## Bounded delegation

For substantial construction, proactively delegate work only when it is **Bounded**, **Independent**,
and **Verifiable**. Keep ambiguous architecture and tightly coupled decisions with the lead; do tiny
jobs locally. `[manual]`

- At most **two active workers**, one level deep: `Ali → lead → worker`. Workers never spawn
  helpers. The cap is `[testable]`; the one-level instruction remains `[manual]`.
- Give each worker only `Goal | allowed files | interface/inputs | acceptance checks | exclusions`.
  Use non-overlapping file ownership and tell writers they share the repo and must preserve others'
  changes. `[manual]`
- Workers do not redesign, commit, push, merge, handle secrets, or touch production. A worker stops
  and reports ambiguity instead of widening its packet. `[manual]`
- Return `changed files | checks/results | unresolved issues`. The lead inspects the complete diff
  and reruns relevant checks; worker completion is not phase acceptance. `[manual]`

## Native tooling and standalone launcher

Use native subagents when available. [`.codex/agents/`](../../.codex/agents/) defines builder and
mechanic workers with `workspace-write` and scouts with `read-only`. The roles describe task shape;
both writing roles use Luna High. `[testable]`

[`.codex/config.toml`](../../.codex/config.toml) sets
`agents.max_concurrent_threads_per_session = 2`. The cap and role sandboxes are checked against
[`invariants.json`](../../invariants.json) by `scripts/check-invariants.sh`. No worker may use
`danger-full-access`. The sandbox is a filesystem boundary; it is not evidence of production
authorization or a substitute for withholding credentials. `[testable/manual]`

The existing [`bin/agent`](../../bin/agent) mirrors the routing table for standalone sessions:

```bash
bin/agent lead "<authorized packet>" --tier astra --dry-run
bin/agent lead "<authorized packet>" --tier terra --dry-run
bin/agent lead "<authorized packet>" --tier sol --dry-run
bin/agent review "<merged-result review packet>" --dry-run
bin/agent scout "<bounded inspection>" --dry-run
bin/agent builder "<bounded implementation>" --dry-run
bin/agent mechanic "<specified edits>" --dry-run
```

Preview with `--dry-run`, then omit that flag to launch. Lead defaults to Terra High; `--tier` is
lead-only and the packet overrides the default. Review inherits the harness's configured model and
effort; `AGENT_REVIEW_MODEL` and `AGENT_REVIEW_EFFORT` optionally override them. No model or effort
is required by the review process. Review uses a writable construction checkout so it
can author the review/planning PR, with no production authority. `AGENT_MODEL_ASTRA`,
`AGENT_MODEL_TERRA`, `AGENT_MODEL_SOL`, and `AGENT_MODEL_LUNA` are explicit identifier overrides;
the operator must verify availability before launch. `tests/agent-test.sh` checks the resolutions
and invalid combinations. A dry-run proves argument construction, not remote model execution.

## Isolation and continuity

Use an isolated checkout when live timers/reconcilers consume the main checkout. Otherwise worktrees
are optional and useful when concurrent edits need separate filesystem state. `--cwd` accepts only
an exact registered Skynet worktree root; arbitrary directories and subdirectories are refused.
Workers edit; the lead commits. `[testable/manual]`

For work crossing sessions, keep a compact ignored `.agent/CHECKPOINT.md` with `Goal`, `Done`,
`Current`, `Decisions`, `Dead ends`, `Verified`, and `Next`. Write it at a meaningful milestone or
handoff. Move durable evidence to its authoritative home and remove the disposable checkpoint at
completion. Do not use transcripts or a second tracker as the handoff. `[manual]`

## Trust and complexity

Construction never grants production authority: no production credentials, root grants, or T2/T3
actions go to workers. Authored PRs remain human-merged. See [`git.md`](git.md) and the constitution.
Keep native tooling and ordinary Git; add no scheduler, queue, workflow database, retry framework,
automatic model router, or automatic session/merge machinery. `[manual]`
