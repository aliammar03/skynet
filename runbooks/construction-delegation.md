---
summary: "Run a construction job as a lead with bounded helpers — decide→BIV→route→invoke bin/agent→verify→integrate→PR — without gaining any production authority."
trigger: "Build X with a couple of helpers / delegate this bounded chunk / run a lead+helper construction job"
---

# Runbook — construction delegation (lead + bounded helpers)

**Trigger:** *"Build X with a couple of helpers"* / *"delegate this bounded chunk"* — any
**build-time** task where a lead wants to hand narrow work to a smaller agent and integrate the result.
**Tier:** **T1, build-time only.** Helpers get **no** production authority — no secrets, no tokens, no
T2/T3 grant. Each helper's sandbox (writers `workspace-write`, scout `read-only`) is the entire leash.

> This runbook is the *procedure*. The *doctrine* (roles, the BIV test, tier routing, the trust
> boundary, "complexity must be earned") lives in [`../docs/conventions/construction.md`](../docs/conventions/construction.md)
> and is the authority if the two ever disagree. Born of
> [SKY-022](../planning/ideas/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md).

## 1. First, decide whether to delegate at all

The default is `one task → one lead → done`. Delegate **only** when it cuts cognitive load or
elapsed time by more than the coordination it adds. If in doubt, don't — do it yourself.

## 2. Gate every hand-off through BIV

A subtask is delegatable only when it is:

- **Bounded** — you can state success in one sentence;
- **Independent** — it needs no constant back-and-forth;
- **Verifiable** — you can cheaply inspect or test the result.

If it fails any of the three — "figure out the architecture", "make this better", anything with
live ambiguity — **keep it**, or send it back to Ali. A bigger model is not a substitute for a clear
objective.

## 3. Route by task *shape* → role → tier

| The subtask is… | Role | Tier · effort | Writes |
|---|---|---|---|
| architecture / cross-cutting / ambiguous — the hard core | *(keep it)* / hard-lead | Terra→**Sol** · xhigh | — |
| **novel bounded logic** behind an interface, with tests | **Builder** | Terra · high | workspace |
| **fully-specified, low-context** repetitive edit / rename / fixture | **Mechanic** | Luna · high | workspace |
| **read-only** search / compare / investigate | **Scout** | Luna · medium | none |

The tell: **Terra unless the job is tightly specified and low-context — then Luna** (Luna
context-rots and over-codes on vague specs). At most **two** active helpers, **one** delegation level
(a helper never launches its own helper). Details + evidence: the doctrine spoke.

## 4. Write a real helper prompt

A helper with a vague prompt is *your* bug, not its. Every prompt states, explicitly:

1. **Scope surface** — the exact files/dirs it may touch, nothing else.
2. **Expected output** — the concrete deliverable, and its shape.
3. **Write allowance** — for a writer, "edit only the scope files; do **not** commit / push / touch git."
4. **Verification** — the exact commands it must run before reporting (and paste the output).

## 5. Invoke, verify, integrate

```bash
# preview the resolved role→tier→model→sandbox first — launches nothing:
bin/agent <scout|builder|mechanic|lead> "<prompt>" --dry-run
# then for real (drop --dry-run). --hard promotes a lead Terra→Sol.
bin/agent scout   "<read-only investigation prompt>"
bin/agent builder "<bounded-logic prompt>"
```

- `bin/agent` runs a `codex exec` process, sandboxed to the role. The transcript streams to
  **stderr**; the helper's **final report is on stdout**. Wait on process exit, not on output bytes.
- If the lead session is itself Codex, prefer **native in-session** delegation (the `.codex/agents/`
  definitions enforce the ≤2 cap); `bin/agent` is the standalone mirror for any other lead engine.
- **The helper's "done" is a claim to verify, never a merge signal.** Re-check every `file:line` a
  scout cites; read a writer's full diff; run the gates **yourself**
  (`./scripts/check-invariants.sh`, the relevant `tests/*-test.sh`). Prove a new gate actually
  *catches* a violation, not just that it passes clean.
- **You integrate and you own the PR.** Wire in anything the helper couldn't (CI, catalog rows),
  then land it as a PR — and **never self-merge** ([`../docs/conventions/git.md`](../docs/conventions/git.md)).

## 6. Continuity for a long job

If the task may cross a session/context boundary, keep a compact, gitignored `.agent/CHECKPOINT.md`
(shape + write-triggers in the doctrine spoke). A cold lead resumes from **only** `AGENTS.md` + the
`SKY-###` phase + the checkpoint + `git status`/`git diff`. Delete it on completion after durable
facts move to their real home.

## 7. Worked example

To make the construction doctrine's `[testable]` claims enforceable, the lead split the job into
a read-only investigation and a bounded implementation.

- A Scout located every claim, the enforcement gap, the exact configuration literals, and the
  existing test/CI wiring. The lead re-checked every cited file and line before using that report.
- A Builder received a BIV prompt: edit only `invariants.json`, `scripts/check-invariants.sh`, and
  `tests/construction-test.sh`; add the specified checker and tests; do not commit, push, or touch
  Git; then run `./scripts/check-invariants.sh` and `./tests/construction-test.sh`.
- The lead read the complete diff and independently reran the invariant gate, construction test,
  and JSON validation.
- To prove the new controls failed closed, the lead temporarily changed the helper cap from two to
  three and the Scout sandbox from `read-only` to `workspace-write`; each mutation failed with an
  actionable message, and the lead restored the clean configuration.
- Finally, the lead wired the test into the pre-commit hook and CI, updated the doctrine's checker
  references, and opened PR #173.
