---
summary: "The construction delegation contract: one accountable lead hands bounded, independent, verifiable work to at most two helpers, one level deep, native tooling first — and no helper ever gains production authority."
---

# Spoke · Construction delegation (lead + bounded helpers)

> One capable **lead** owns a construction task end to end. It may hand narrow jobs to a small bench
> of **helpers**, integrate the result, and stay understandable enough that Ali can reason about the
> whole thing from memory. This is a **build-time** pattern only — production operation stays behind
> the trust model and `bin/ops`. Governed by [`../conventions.md`](../conventions.md); full rationale
> in [`../../planning/ideas/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md`](../../planning/ideas/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md).

Tags: **[testable]** = a lint/config gate could assert it; **[manual]** = holds by review.

## The default is still one agent

```text
one task → one lead → done
```

Delegation is used **only** when it cuts cognitive load or elapsed time by more than the
coordination it adds. A bigger fan-out is not the goal.

## Roles → GPT-5.6 tier

Roles are the stable contract; the model behind a role is configuration and swaps freely.

| Role | Owns | Tier (GPT-5.6) | Writes? |
|---|---|---|---:|
| **Lead** | Intent, architecture, decomposition, integration, verification, the PR | **Terra** (→ **Sol** for genuinely hard / cross-cutting work) | yes |
| **Builder** | One bounded component behind a clear interface | **Terra** | yes |
| **Mechanic** | Repetitive edits — fixtures, renames, formatting, routine docs | **Luna** | yes |
| **Scout** | Search / compare / investigate, returns a concise report | **Luna** (Terra if the reasoning is hard) | **no** |

Sol is the flagship (hardest problems), Terra the balanced workhorse, Luna the fast/cheap tier for
repeatable objective-check work. The lead is **accountable for the whole result**; a helper can
report only *"my delegated subtask is complete,"* never *"the phase is complete."* `[manual]`

## Delegation depth = one

- **Allowed:** `Ali → lead → helper`. `[manual]`
- **Never:** `Ali → lead → helper → helper → …`. One level keeps context ownership and failure
  diagnosis obvious. `[testable]`
- **At most two active helpers.** `[testable]` Raise the cap only after real work proves two is
  constraining — not on aesthetics.

## Delegate only what passes the BIV test

A subtask is delegatable only when it is:

1. **Bounded** — success can be stated in one sentence;
2. **Independent** — it needs no constant back-and-forth with the lead;
3. **Verifiable** — the lead can cheaply inspect or test the result. `[manual]`

Good: *"Find every call site assuming the old entity ID; report file + function."* ·
*"Update these fixtures to schema v2; touch no production code."* ·
*"Implement parser X behind this interface and run tests A/B."*

Bad: *"Figure out the architecture."* · *"Make this subsystem better."* · *"Decide what to build."*
Ambiguity stays with the lead or goes back to Ali.

## Native tooling first

Use Codex's own subagent support — do not build a scheduler around it. `[manual]`

- Project-scoped agent definitions live in [`.codex/agents/`](../../.codex/agents/) (`builder.toml`,
  `mechanic.toml`, `scout.toml`); each names its own `model`, `model_reasoning_effort`, and
  `sandbox_mode`. The lead is the invoking session, not a definition file.
- [`.codex/config.toml`](../../.codex/config.toml) sets `[agents]
  max_concurrent_threads_per_session = 2` — the two-helper cap enforced by the platform, not by
  vigilance. `[testable]`
- The **scout** definition pins `sandbox_mode = "read-only"` — its no-write contract is mechanical,
  not a promise. `[testable]`
- For a helper run as its own process (or to preview a launch), [`bin/agent`](../../bin/agent)
  resolves `role → tier → model` and prints the resolution under `--dry-run`. It is the standalone
  mirror of the same routing table above; if native in-session delegation expresses the job, prefer
  it.

## Isolation, continuity, review

- **Worktrees by exception.** `[manual]` A read-only scout needs none; a single writing helper inside
  a lead-managed session usually needs none. Reach for `git worktree` only when two independent
  writers genuinely need separate filesystem state. Git is the isolation mechanism — SKY-022 builds
  no worktree manager. (Proven in [SKY-022 Phase 4](../../planning/ideas/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md).)
- **Continuity is a checkpoint, not a memory system.** `[manual]` For a task likely to cross a
  session boundary, the lead keeps a compact `.agent/CHECKPOINT.md` (gitignored, disposable). On
  completion, durable facts move to their real home — directive / docs / ADR / journal / git — and
  the checkpoint is deleted. (Detailed in [SKY-022 Phase 3](../../planning/ideas/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md).)
- **Review lives outside the helper family.** `[manual]` A helper never reviews the lead that
  instructed it. Normal changes ride existing tests/gates + human merge; consequential ones may get a
  fresh cold Sol review, sensitive cross-provider ones a Claude review. Deterministic gates outrank
  every model opinion.

## The trust boundary — construction never gains production authority

- A construction helper **never** receives production credentials, a standing token, or a T3 grant.
  `[manual]` Its blast radius is the repo working tree plus whatever least-privilege sandbox its role
  declares (writers `workspace-write`, scout `read-only`).
- Parallelism at build time must **never** become a second production-control path. Production
  operation stays behind the trust tiers and `bin/ops`. `[manual]`
- Authored work still lands as a **PR the agent never self-merges** — delegation changes who *drafts*
  a change, never who *merges* it. `[manual]` → [`git.md`](git.md)

## Complexity must be earned

SKY-022 deliberately ships **no** queue, scheduler, workflow database, event ledger, DAG engine,
heartbeat, worker lease, retry framework, or automatic-merge machinery. If repeated dogfooding
exposes a concrete failure mode, automate *that* failure mode specifically — nothing sooner.
