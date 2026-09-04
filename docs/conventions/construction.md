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

| Role | Owns | Tier (GPT-5.6) | Effort | Writes? |
|---|---|---|---|---:|
| **Lead** | Intent, architecture, decomposition, integration, verification, the PR | **Terra** (→ **Sol** for genuinely hard / cross-cutting work) | **xhigh** | yes |
| **Builder** | One bounded component behind a clear interface | **Terra** | **high** | yes |
| **Mechanic** | Repetitive edits — fixtures, renames, formatting, routine docs | **Luna** | **high** | yes |
| **Scout** | Search / compare / investigate, returns a concise report | **Luna** | **medium** | **no** |

Sol is the flagship (hardest problems), Terra the balanced workhorse, Luna the fast/cheap tier for
repeatable objective-check work. **Route by uncertainty and consequence, not prompt length** — and
the Terra↔Luna choice *is* the Builder↔Mechanic split:

- The **lead** carries the uncertainty and consequence, so it reasons hardest — **xhigh** — because
  reasoning effort, *not* tool access, is what buys first-try reliability (raising a planning turn
  high→xhigh moved perfect first runs 28%→89% for +9–29% cost). Terra by default; **Sol** for
  architecture / cross-cutting / ambiguous work. Only Sol supports **`max`** — reserve it for a
  genuinely brutal hard-lead task.
- **Builder → Terra.** Novel bounded *logic* is where correctness margin matters: Terra wins every
  coding benchmark (Terminal-Bench 87.4 vs 84.7, SWE-Bench Pro 63.4 vs 62.7, Coding-Agent-Index 77.4
  vs 74.6) and is the documented pick for coding-agent / CI loops. The saving from Luna on one small
  component is ~2.5×/token on a *tiny* base; a wrong builder costs a rework loop paid in **expensive
  lead** tokens, which dwarfs it. Escalate to xhigh only if corrective prompts prove costly.
- **Mechanic → Luna.** High-*volume*, deterministic edits with airtight objective checks are exactly
  where Luna's economics + steep effort curve win: scaling — not per-call cost — dominates, and
  strong checks make a premium model pointless. Run it at **high** (Luna is cheap enough that high is
  affordable across many edits). Read-only **Scout → Luna medium**.
- **The operational tell (practitioner-reported):** Luna suffers *context rot* as context fills and
  *over-codes on vague specs* — so it shines only on a tightly-specified, low-context job. That is the
  Mechanic's and Scout's profile, not the Builder's. If a "Builder" subtask is really a fully-spelled,
  low-context transform, Luna fits; if it needs judgement or carries surrounding-code context, keep it
  on Terra. The BIV **B**ound has to be *tight* before a job drops a tier.

The lead is **accountable for the whole result**; a helper can report only *"my delegated subtask is
complete,"* never *"the phase is complete."* `[manual]`

## The lead's playbook (quick reference)

The 30-second version of everything below — what to reach for, when.

1. **Default: don't delegate.** `one task → one lead → done`. Delegate only when it saves more than
   the coordination it costs.
2. **Gate every hand-off through BIV** — Bounded, Independent, Verifiable. If you can't state success
   in a sentence, or you'd have to babysit it, or you can't cheaply check it: keep it, or send it back
   to Ali. Ambiguity is never delegated.
3. **Pick the role by task *shape*, then read the tier off it:**

   | The subtask is… | Role | Tier · effort | Writes |
   |---|---|---|---|
   | architecture / cross-cutting / ambiguous — the hard core | *(keep it)* / hard-lead | Terra→**Sol** · xhigh (Sol-only `max` if brutal) | — |
   | **novel bounded logic** behind an interface, with tests | **Builder** | **Terra · high** | workspace |
   | **fully-specified, low-context** repetitive edit / rename / fixture | **Mechanic** | **Luna · high** | workspace |
   | **read-only** search / compare / investigate | **Scout** | **Luna · medium** | none |
   | "make it better" / "decide what to build" / vague | **don't delegate** | — | — |

4. **The tier tell:** Terra unless the job is *tightly specified and low-context* — then Luna. Luna
   context-rots and over-codes on vague specs, so a loose "Builder" chunk stays Terra; a Builder is
   cheap to run but a *wrong* one costs a rework loop in expensive lead time. When unsure, spend the
   Terra token, not the rework.
5. **Invoke** — native in-session (preferred): ask Codex to spawn the `builder`/`mechanic`/`scout`
   agent (defs in `.codex/agents/`, cap = 2). Standalone or to preview: `bin/agent <role> "<prompt>"
   [--hard] [--dry-run]` — always `--dry-run` first to see the resolved model/effort/sandbox.
6. **Write a real helper prompt:** state the scope surface, the expected output, the write allowance,
   and the exact verification (which tests/gates). A helper with a vague prompt is your bug, not its.
7. **Integrate + own it:** you inspect the returned work, run the gates yourself, and land the PR.
   The helper's "done" is a claim to verify, never a merge signal — and you never self-merge (§ trust
   boundary).

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
