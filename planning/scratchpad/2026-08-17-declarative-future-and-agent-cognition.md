# scratchpad — 2026-08-17 · What Skynet is, and where the declarative future goes

> Raw brain-dump. No ID, no commitment. The thesis + a pile of concrete follow-on ideas about
> imperative work, events, agent memory, and the NixOS-vs-OpenTofu question. Ends with a research
> queue → things to chew on in spare time before any of this earns a SKY-###.

---

## 0. The reframe (the load-bearing idea)

Ali called Skynet "CI/CD and declarative." That undersells it. The real thesis is already in the
constitution:

> it is stateless by design, and everything it is stands in git.

**Skynet isn't a CI/CD pipeline with an agent attached — it's a stateless intelligence whose entire
memory and body are a git repo.** GitOps is *downstream* of that, not the point.

Why this matters: classic declarative IaC (Terraform, k8s, GitOps) is a workaround for **human**
limitations — humans forget state and botch imperative sequences, so we write desired-state and let
a dumb-but-reliable reconciler converge. Determinism is the feature; the reconciler is dumb on
purpose.

An LLM agent is the opposite of a dumb reconciler. So the honest question is: does it even *need*
declarative IaC? Answer: **it needs it more than a human does, but for a different reason.** Not
because the agent is dumb — because it's *amnesiac*. Every session is a fresh mind that reconstructs
the world from git before it can act. Declarative git-as-truth isn't deployment mechanics here —
**it's the externalized cognition substrate.** Optimize for *that*, not for deploy throughput, and
the roadmap writes itself.

### What the current design gets right (for an LLM operator)
The right objective isn't "efficiency" in the human/CI sense. It's:
- **Legibility** — can a cold-booting agent cheaply reconstruct full state? Markdown + JSON
  inventory + rendered docs = very high. Biggest strength, not an accident.
- **Reversibility** — `git revert` → Arcane converges back. Reversibility is an *intelligence
  multiplier* for a non-deterministic operator: it can act boldly because mistakes are cheap.
- **Low branching factor** — compose + Arcane is a small, boring surface. Fewer abstractions = less
  to get wrong. Keeping this low even at the cost of raw capability is *correct* at this maturity.

## 1. The leak: declarative for services, imperative for infrastructure

The declarative boundary currently **stops at the Docker layer.**

- **Above the line (declared, git→reality):** `compose/<svc>/` → Arcane reconciles.
- **Below the line (imperative, human-driven):** provisioning a VM = `runbooks/provision-vm.md` +
  a script. Onboarding a host = a script. Firewall/DNS = done by hand; firewall only *mirrored*
  into git after the fact (os-git-backup) — that's **observed** truth, not **desired** truth.

So there are two kinds of truth flowing in opposite directions:
- `compose/` = **desired** state, git → reality (Arcane).
- `inventory/` + firewall mirror = **observed** state, reality → git (render-docs, os-git-backup).

**The gap: nothing closes the loop between them.** Drift (desired − observed) is noticed only when
an agent happens to read inventory. In control terms: a plant, two sensors, no controller wiring the
error signal back. **This is the single biggest latent idea in the system.**

Two north-star directions fall out of this:
- **A. Close the control loop** — make drift a first-class, continuously-monitored signal; move from
  batch (poll + nightly) to event-driven; walk the autonomy ratchet until the agent is a *supervised
  reconciler*, not just a proposer. The ratchet's endgame *is* "agent becomes a smart reconciler."
- **B. Push the declarative boundary downward** — from "declarative services on imperatively-
  provisioned infra" toward declaring the infra too (VMs, DNS, host config). This is the NixOS /
  OpenTofu question (§5).

Contrarian guard-rail: **don't over-declarative-ize.** Incident diagnosis, exploration, one-off
forensics are inherently imperative and the agent is *good* at them. The art isn't "make everything
declarative" — it's knowing which layer deserves which paradigm. The current split is a feature.

---

# BUILD-ON — concrete ideas

## 2. Better imperative work: exploration, diagnosis, fixing

The imperative side (runbooks + auto-expiring root grants + scripts) is the right *shape* but thin.
Make it a real discipline.

### 2a. A standing recon toolkit (T1, always available)
A structured, read-only `scripts/recon.sh` the agent runs *first* on any host it's puzzling over:
services, unit states, recent logs, disk/mem/cpu, listening ports, recent package/config changes,
container health. Emits **one structured snapshot** the agent reasons over instead of firing 20
ad-hoc commands. Lowers the cost of "what's going on here" to near-zero and keeps exploration inside
T1 (no grant needed just to look). Feeds the journal (§4).

### 2b. A diagnosis library, not rigid scripts
LLM-guided diagnostic runbooks for common failure classes — container crash-loop, disk full, cert
expired, DNS resolution fail, backup failed, Arcane stuck, restic/PBS timer missed. Each embeds the
*diagnostic* commands + decision branches, but leaves judgement to the agent. Extends the existing
runbooks into a real triage tree.

### 2c. The principle: **diagnose imperatively, fix declaratively**
The root grant is for *understanding*. The *fix*, wherever possible, routes **back through the
declarative loop** — a fix is a PR to `compose/` / a nix module / a tofu resource, not an imperative
one-off. This is what keeps drift from accumulating. When a fix *must* be imperative (emergency),
it's immediately reconciled back into declared state — **no orphan fixes.** Worth promoting to a
constitution principle.

### 2d. A lab bench (safe reproduction / simulation)
The agent needs somewhere to test a fix before applying. Candidates already exist: `vm-docker-dmz`
is memory-tagged throwaway/destructive-OK — formalize it as the agent's bench. Plus dry-run
primitives per layer: `tofu plan`, `nixos-rebuild dry-activate`, compose in a throwaway context.
"Try it on the bench, show the diff, then propose" becomes the default reflex.

### 2e. Incident records → memory
Every diagnosis session ends with a dated incident note in the journal (§4): symptom, what was
checked, root cause, fix, whether the fix was declarative. Failed hypotheses included — negative
results are memory too.

## 3. Events: from batch to reactive

Today: Arcane polls git; nightly cron reports at 03:30. Pure batch. The observability spoke already
flags the gap — **no signal fires between nightlies.**

### 3a. Event sources worth wiring
GitHub webhook (merge → deploy-verify), Renovate PR opened, health-check failure, **drift detected**
(§3c), backup failed, root-grant nearing expiry, disk threshold crossed, container crash-loop, cert
near expiry.

### 3b. The wake pattern (respecting the ratchet)
A lightweight webhook receiver on the ops VM classifies an event and either:
- **(report-only, default)** files a note + ntfy alert and proposes; or
- **(auto-approve)** runs a scoped capability — *only* for event→action pairs promoted onto the
  auto-approve list, one PR at a time.

ntfy is already in the design for grant-approval; the same channel carries event alerts. This is the
autonomy ratchet applied to *reactivity*: reactive-but-report-only first, reactive-and-acting later,
per graduated pair.

### 3c. Drift as an event = the control loop closing
A periodic/triggered diff per layer — `tofu plan`, `nixos-rebuild dry-activate`, `compose` config
diff, firewall mirror vs. a declared baseline — emits a **drift event** when desired ≠ observed.
*This is literally §1's controller.* Even report-only, it turns "someone changed the firewall by
hand" from invisible-until-nightly into an immediate signal.

## 4. Perfect memory: fix the episodic gap

Break agent memory into four kinds and score Skynet honestly:

| Kind | What | Skynet today |
|---|---|---|
| **Working** | context window | fine (stateless by design) |
| **Semantic** | facts / current state | **strong** — MEMORY.md, docs/, inventory/, generated/ |
| **Procedural** | how-to | **strong** — runbooks/, scripts/, bin/ |
| **Episodic** | what *happened*, the trajectory | **weak** — only raw git history + progress memories |

**Skynet's memory gap is episodic.** Git stores everything, but a cold agent can't efficiently
reconstruct *how the lab got here, what was tried, what failed.* Storage isn't the problem —
**retrieval** is.

### 4a. A journal (the missing episodic store)
`journal/` (or extend nightly): dated, append-only session/incident/decision records — intent,
actions, grants used, outcome, and crucially **what was tried and abandoned** (a "graveyard"). This
is the immutable episodic log git history *implies* but isn't shaped for.

### 4b. Retrieval, not just storage
- **Rolling digest** — extend `05-state-of-the-lab.md` into a maintained "state + recent decisions +
  open threads" digest the agent reads on cold-boot. Cheap, high-leverage, no new infra.
- **Semantic index (bigger swing)** — a *locally-regenerable* embedding index over repo + journal so
  a cold agent retrieves relevant past context by similarity, not by grepping 6 months of history.
  Must be **rebuildable from git** to preserve statelessness — the index is a cache, git is truth.
- **Decision memory** — ADRs already exist in `docs/decisions/`. Enforce: every non-trivial choice →
  ADR, so the agent never re-litigates a settled question. `[[SKY-###-progress]]` memories already
  do a lighter version of this.

### 4c. The "why" layer
Git says *what* changed; commit messages hint at *why*. Perfect memory needs the reasoning traces —
session rationales attached to their commits/PRs. The PR-to-teach culture already pushes this way;
make it explicit so intent survives.

---

## 5. NixOS fleet vs OpenTofu — the real evaluation

**First, kill the "vs".** They mostly aren't competitors — they own **different layers**:

- **OpenTofu = provisioning / lifecycle.** Creates and destroys *resources* via providers: Proxmox
  VMs/CTs, cloud-init, DNS records, pools/ACLs. Real dependency DAG, `plan` before `apply`, drift
  detection. It makes the box *exist*. It does **not** configure inside the OS well.
- **NixOS = host definition.** The whole machine — packages, services, users, docker, SSH trust — as
  one reproducible expression. `nixos-rebuild switch`; atomic rollback via boot generations; **drift
  structurally impossible** inside the declared surface. It defines *what's on* the box. It does
  **not** create the VM.

**The synthesis: Tofu provisions the box, Nix defines what's on it.** The real question isn't which
one — it's *which layers each owns, and how far down the stack we dare push declaration.*

### 5a. Capabilities & fit for Skynet

**OpenTofu**
- Providers: Proxmox (bpg/telmate), a DNS provider or a thin custom one for Technitium zones.
- Turns `provision-vm.md` from an imperative runbook into a declared resource — and `tofu plan` is a
  *perfect* LLM primitive: agent proposes, plan shows the exact diff, human reads it, apply. Same
  propose/dispose shape you already have, extended to infra.
- **Tradeoffs:** state file is critical and **contains secrets** → needs an encrypted backend (sops
  pattern already in-house). Proxmox providers can be finicky. Doesn't configure inside the box.
  Another paradigm to hold.

**NixOS (fleet: colmena / deploy-rs / flakes)**
- The *most* declarative option. For an amnesiac agent it's close to ideal: the repo doesn't just
  *describe* the host, it *is* the host, deterministically. Cold-boot legibility is maximal.
- **DR win:** rebuild any host from a flake — directly strengthens the disaster-recovery spoke.
- **Trust-model win (big):** "T2+ root grant to harden a host" collapses into "PR a nix module."
  A whole imperative escape hatch becomes declarative, reviewed, reproducible. Hardening leaves a
  git-reviewable trace instead of a mutable snowflake.
- **Secrets synergy:** `sops-nix` / `agenix` plug straight into the existing **sops+age** setup
  (needed because `/nix/store` is world-readable — never put secrets in a plain nix value).
- **Impermanence option:** wipe root on boot, persist only declared paths → compromise doesn't
  persist. Strong security posture, but advanced.
- **Tradeoffs:** steep. The **LLM must be genuinely good at Nix** — cryptic errors, sharp ecosystem
  edges, build times, packaging friction for oddball software. This is the real risk and must be
  de-risked before betting hosts on it.

### 5b. How much infrastructure can come under each umbrella — *safely*

Mapping against the trust tiers (this is the security-critical part):

**Safe under OpenTofu (T2-ish, PR-gated):**
- `ops-managed` VM/CT lifecycle + cloud-init.
- Technitium **zone records** (already T2).
- *Carefully:* Proxmox pool membership / operate ACLs — but pool membership **is the blast-radius
  dial**, so declaring it in Tofu means the dial lives in a tofu file → any change is a
  `docs/system-design.md` PR anyway. Handle with the same ceremony, don't let Tofu quietly widen it.

**Off-limits to Tofu:**
- OPNsense (T3; no clean declarative story — os-git-backup mirror stays the model).
- The excluded guests: **VM 5001, CT 635, CT 837, Unraid VM 2020** — seen at T1, touched never.
- Anything that would give the tofu token a standing path into T3.

**Safe under NixOS:**
- Any workload host we're willing to convert — starting with **the ops VM itself
  (`vm-skynet-ops`)**. Making Skynet's *own brain-host* a NixOS flake is the ideal pilot: lowest
  blast radius (it's the agent's own house), highest payoff (perfect reproducibility + DR of the
  agent itself), and the place to prove the LLM can actually operate Nix before betting other hosts.
- Then new/rebuilt workload hosts, one at a time — an onboarding, not a redesign.

**Never NixOS (leave alone):** OPNsense, Unraid, the excluded appliances — not general-purpose Linux
we control.

### 5c. Security benefits & tradeoffs, summarized

**Benefits (both):** declared state = auditable, reviewable, reproducible; no snowflakes; diff-before-
apply; drift becomes visible. **Nix specifically:** collapses imperative root-hardening into reviewed
config; atomic rollback makes hardening safe to iterate; impermanence caps compromise persistence;
the entire host is a git diff.

**Tradeoffs / new risks:** Tofu **state file = a new secret** (encrypt it, scope its token). Nix
**secrets need sops-nix/agenix** (store is world-readable). **Provider/deploy tokens are new standing
credentials** — must be scoped to the operate tier, never a back-door into T3. And the meta-risk:
**every new paradigm raises the branching factor** — the thing we've been *right* to keep low. Nix
especially only pays off if the agent is genuinely fluent; a half-fluent agent on Nix is *more*
dangerous than a fluent one on compose.

### 5d. Tentative shape (not a decision — a hypothesis to test)
- **Layer 1 — provisioning:** OpenTofu owns ops-managed VM/CT lifecycle + Technitium zones. Safe,
  incremental, high-value, `plan` fits the LLM perfectly. *Most likely first real bet.*
- **Layer 2 — host definition:** NixOS, piloted on `vm-skynet-ops` only, as a de-risking experiment.
  Expand to workload hosts *only* if the pilot proves the agent operates Nix reliably.
- **Layer 3 — services:** stays compose + Arcane for now. Nix-native services (arion / oci-containers)
  is a *much* later question and probably not worth the churn.
- **Untouched:** OPNsense + excluded appliances stay exactly as they are. The declarative wave stops
  at the T3 boundary, always.

---

## 6. Research queue — spare-time reading → then move decisions to backlog

Each item names *what to learn* and *what decision it unblocks*. When one resolves, `bin/plan idea`
it, then promote to backlog.

1. **OpenTofu + Proxmox provider (bpg).** Read the provider docs; watch a "VM from cloud-init via
   tofu" walkthrough. → *Decision: adopt Tofu for ops-managed VM lifecycle? (likely yes)*
2. **Tofu state backends + secret handling.** Encrypted state, remote vs local, sops pattern.
   → *Decision: where does state live, which token scopes it?*
3. **Technitium as tofu-managed DNS.** Is there a usable provider, or do we write a thin one against
   its API? → *Decision: DNS zones as declared resources, or stay UI/script?*
4. **NixOS fundamentals + flakes.** Enough to read/write a module confidently. This is the gating
   skill for everything Nix. → *Decision: is Nix fluency realistic for the agent + Ali?*
5. **NixOS fleet deploy: colmena vs deploy-rs.** Push model, rollback, secrets. → *Decision: fleet
   tool if we pilot.*
6. **sops-nix / agenix.** How Nix secrets ride the existing sops+age. → *Decision: secrets story for a
   NixOS host.*
7. **NixOS impermanence ("erase your darlings").** Security posture, persistence model.
   → *Decision: worth it for hardened hosts, or too advanced for now?*
8. **Event bus / webhook-to-agent patterns.** ntfy triggers, a tiny webhook receiver, GitHub webhooks.
   → *Decision: shape of the reactive layer (§3).*
9. **Drift detection as signal.** How `tofu plan` / `nixos-rebuild dry-activate` / compose-diff can be
   scheduled and turned into an event. → *Decision: how the control loop closes (§1/§3c).*
10. **Agent episodic memory / retrieval.** Local embedding index rebuildable from git; journal design.
    → *Decision: build a `journal/` + digest, and/or a regenerable semantic index (§4).*
11. **k3s sanity check (to reject on purpose).** Confirm the branching-factor cost isn't worth it at
    homelab scale, and write down *why* as an ADR so it stays rejected. → *Decision: formally not-k8s.*

---

## 7. One-line takeaways
- Skynet = a stateless mind whose memory is git. Optimize the repo as cognition, not as a pipeline.
- The control loop is open — closing it (drift-as-event, supervised reconciler) is the biggest win.
- Diagnose imperatively, **fix declaratively**; no orphan fixes.
- Memory gap is **episodic** — build a journal + retrieval, not more storage.
- Tofu and Nix aren't rivals: **Tofu makes the box exist, Nix defines what's on it.** Pilot Tofu on
  VM lifecycle, pilot Nix on the ops VM's own host, keep the wave clear of the T3 boundary.
