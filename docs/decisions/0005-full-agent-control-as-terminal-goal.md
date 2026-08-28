# ADR 0005 — Full agent control is the terminal goal; autonomy is earned, reversible, and never self-granted

- **Status:** accepted
- **Date:** 2026-08-28

## Context

The constitution has always described *where the leash sits* — never *where it is going*. §2b calls
autonomy a "version-controlled dial" and §6 lists growth directions, but nothing states the terminal
condition the dials are being turned toward. That omission has a cost: every autonomy question gets
re-argued from first principles, and each individual loosening looks like erosion rather than a step
on a declared path.

The goal, stated plainly: **Skynet runs the lab. A human expresses intent — "deploy this service" —
and the system delivers it: provisioned, published, backed up, monitored, and documented, with no
further input.** The agent corrects service drift, provisions and optimises workloads, validates
firewall rules, and keeps its own backups honest. The heart of the system is the AI; the scripts,
gates, and runbooks exist to make the AI's judgement safe to act on, not to replace it.

**Why the leash exists today is worth being precise about, because it determines what removes it.**
The binding constraint is *not* an external adversary — that threat is real and separately handled
(scoped tokens, segmentation, no standing T3). The binding constraint is that **the agent is
unproven**: an LLM operator can be confidently wrong, and a confidently-wrong actor with T2 write
across two nodes can do real damage in one run. Today the only thing standing between a plausible-
but-wrong plan and the lab is **a human reading a diff**.

That reframes the entire problem. Every widening of autonomy is really one question:

> **What replaces the human as the verifier of this specific loop?**

If nothing replaces them, the widening is not a graduation — it is just the removal of a check.
Autonomy therefore cannot be *granted*; it has to be *bought*, and the currency is verification.

A second force: the same property that makes the system recoverable makes autonomy affordable.
A stateless system — one where any bad state is fixed by re-derivation from git rather than by
archaeology — is a system in which being wrong is cheap. **Statelessness is not a philosophical
preference sitting beside the autonomy goal; it is the precondition for it.**

## Decision

Adopt **full agent control as the declared terminal goal** of the system, and govern the approach to
it with four rules.

### 1. Autonomy is earned per capability, by evidence

Autonomy is not a global setting. It is a property of an individual **capability** (a named,
scoped action: "restart an unhealthy container", "apply a `tofu plan` with no destroy", "write a
Technitium record"). Each capability sits on a ladder and climbs it on evidence:

| Level | The agent may… | Verified by |
|---|---|---|
| **A0 Observe** | read, render, report | — |
| **A1 Propose** | open a PR; a human merges | a human reading the diff |
| **A2 Rehearse** | execute against the proving ground, not production | the rehearsal's own assertions |
| **A3 Supervised act** | act in production, human notified, easy manual undo | gates + verification, human watching |
| **A4 Auto act** | act unattended within its declared scope | gates + verification + automatic rollback |
| **A5 Self-direct** | choose *when* the capability is needed, not just how | all of the above + drift attribution + budget |

A capability may only advance a level with a recorded track record at the level below — clean
rehearsals, then clean supervised runs — plus the reversibility test in §3. The record lives in git;
promotion is a PR to `AGENTS.md` §3 and this file's ladder. **"It felt fine" is not evidence.**

### 2. The human is replaced by verifiers, in three classes

Nothing graduates until something else does the job the human was doing. Three replacements, in
ascending order of what they can catch:

- **Deterministic gates** — `invariants.json` + `check-invariants.sh` + CI. Absolute, unarguable, and
  limited to violations that can be named in advance. Cheapest and most trustworthy; an LLM cannot
  reason its way past a script that exits 1.
- **Empirical verification** — plan/dry-run diffs bounded before apply, canary scope, post-change
  health probes, and automatic rollback on failure. Catches *"this change does not work"* without
  anyone having predicted the failure. This is the largest currently-missing piece.
- **Adversarial review** — a second agent session, cold, with no shared context, reviewing the diff
  against the constitution and the plan's stated intent. Catches *"this is wrong-headed"* — the class
  gates and probes both miss. Its errors are correlated with the proposer's but not identical,
  especially across engines; it is a real filter, not a rubber stamp, and it never replaces the
  gates below it.

### 3. The reversibility test — the admission criterion for unattended action

A capability may reach **A4** only if its rollback is:

1. **automatic** — it fires without a human noticing first;
2. **tested** — exercised in the proving ground, in the failure case, not just reasoned about; and
3. **independent of the agent** — performed by a dumb executor that works even when the agent's
   judgement is the thing that failed.

Clause 3 is the load-bearing one. `git revert` → Arcane reconciles is safe *because the reconciler is
dumb and separate*. deploy-rs magic-rollback is safe for the same reason. A "rollback" that requires
the agent to notice, diagnose, and act correctly is not a rollback — it is the same failing component
asked to grade itself. **Every actuator admitted to A4 must sit behind a dumb reconciler or an
automatic rollback.**

Actions that are **irreversible by nature** — `tofu destroy`, guest deletion, data deletion,
credential rotation, anything that crosses into T3 — are **permanently hard checkpoints at every
autonomy level, including the terminal one.** Full agent control does not mean the agent may
destroy; it means the agent may build, run, repair, and revert without asking.

### 4. What is never delegated — the counterweight that makes the goal safe to state

Full agent control never includes control over the constraints on agent control. At every level,
forever:

- **The agent never widens its own authority.** Any change to `docs/system-design.md` §2, `AGENTS.md`
  §3/§6, `invariants.json`, or the gate scripts that enforce them is **human-merged, permanently** —
  regardless of how autonomous everything else has become. The agent may propose its own promotion;
  it may never merge it.
- **The signing CA never enters Skynet.** Temporary root stays guaranteed by physics, not policy.
- **The kill switch stays reachable without the agent**, and is drilled.
- **A reviewable artifact always exists.** The agent may eventually merge its own proposals; it may
  never act without leaving a diff and a journal entry that a human can read afterward.

### 5. Statelessness, stated precisely enough to be enforceable

The non-negotiable is that the system is **reconstructable from git, never restored from a backup.**
That requires distinguishing two classes:

- **System** — definitions, configuration, policy, identity, encrypted secrets, inventory, docs.
  Reconstructable from git **alone**. A backup of this class is a convenience and must never become
  a dependency.
- **Payload** — the data services hold (CouchDB documents, libraries, archives). Not reconstructable;
  it must be backed up, encrypted, off-site, and restored *after* the system stands up.

**The invariant: rebuilding from git alone must yield a running, correct, empty lab.** Data restore
is a separate, optional, subsequent step. If any part of the *system* class can only be recovered
from a backup, that is a bug to fix — not a backup to take. Cloud backup of the *payload* class is
expected and is being widened, not restricted, by this ADR.

## Consequences

- **The dials gain a destination.** §2b's levers are no longer a standing question; each is a
  position on a declared path, and each move cites the ladder in §1.
- **"Untested" becomes a buildable problem.** The reason the agent is constrained is lack of
  evidence, so the highest-leverage work is the machinery that produces evidence: a proving ground,
  per-capability track records, and the verification layer of §2. That is [SKY-017](../../planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md).
- **Reversibility is promoted from a virtue to an admission criterion.** Capabilities without a
  dumb, tested rollback simply cannot reach A4, however well they work. This will disqualify some
  otherwise-attractive automation, and that is the point.
- **The separation-of-powers rule is now permanent and explicit.** Previously implied by "widening a
  dial is a PR to this file"; now stated as a law that survives every future loosening.
- **Some autonomy will be rejected on principle, not on risk.** Irreversible actions stay checkpointed
  even when the agent is demonstrably good at them. Accepted deliberately: the cost of a wrong
  destroy is unbounded, and no track record bounds it.
- **The stateless invariant becomes testable.** "Rebuild from git yields an empty running lab" is a
  drill, not a belief — and it belongs in the DR rotation.
