> Agent-generated options research for the terminal goal now in the constitution
> ([system-design §1a](../../docs/system-design.md), [ADR 0005](../../docs/decisions/0005-full-agent-control-as-terminal-goal.md)).
> Judged against ADR 0005's requirements, not against feature lists. Sources cited inline; skeptical
> by design — most of what the market sells for this is Kubernetes-shaped or keeps its state
> somewhere other than git, and both are disqualifying here. Feeds SKY-017.

# What system best achieves full agent control — the options

*Compiled 2026-08-28.*

## 0. The shopping list

ADR 0005 turns the goal into six functions that must exist before autonomy can be bought, plus three
constraints that disqualify candidates outright.

**Functions:** **F1** the loop (what wakes, decides, sequences) · **F2** deterministic gates ·
**F3** empirical verification + automatic rollback · **F4** the proving ground · **F5** adversarial
review · **F6** the track record that turns promotion into a measurement.

**Disqualifiers:** state that lives anywhere but git (breaks §2a's rebuild law) · anything needing a
standing path into T3 · a paradigm large enough to raise the branching factor materially. Those three
kill most of the market before features are even compared.

## 1. Prior art: this problem is twenty-five years old and has a name

**MAPE-K** — Monitor, Analyze, Plan, Execute over shared Knowledge — is the reference architecture
for self-managing systems, from IBM's autonomic-computing programme. Its capability taxonomy,
**self-CHOP** (self-Configuring, self-Healing, self-Optimizing, self-Protecting), is almost verbatim
the list of things Skynet is meant to grow into: set up services, correct drift, optimise, validate
firewall rules.

Mapping Skynet onto it is clarifying — and the holes are exactly the ones already identified:

| MAPE-K | Skynet today | State |
|---|---|---|
| **Monitor** | `collect-*.sh` → `inventory/` | ✅ present, three collector holes |
| **Analyze** | — | ❌ **empty** (drift = intended − observed; SKY-004) |
| **Plan** | the agent | ✅ this is the part Skynet is unusually good at |
| **Execute** | Arcane, `tofu apply`, grant-windowed root | ✅ present, mostly without rollback |
| **Knowledge** | git — inventory, docs, journal, ADRs | ✅ the system's strongest asset |

Two things follow. First, the design is not idiosyncratic — it is a MAPE-K loop with an LLM in the
Plan phase, which is precisely where 2026 research is putting them ([MAPER, SEAMS 2026](https://conf.researchr.org/details/seams-2026/seams-2026-research-track/26/MAPER-Extending-MAPE-K-with-LLM-Based-Reasoning-to-Manage-Unanticipated-Situations-i);
[The Vision of Autonomic Computing: Can LLMs Make It a Reality?](https://arxiv.org/html/2407.14402)).
Second, the missing piece is **Analyze**, not Plan — the system has a brilliant planner wired to no
error signal.

Two calibrations from the wider field, both worth holding onto:

- **The 2026 guardrail consensus is ADR 0005's structure, independently arrived at**: *"that separation
  between probabilistic reasoning and deterministic execution is what makes autonomy safe enough to
  run in production"*, with *"policy-as-code versioned and enforced by the execution layer … an
  envelope the agent cannot violate because the action is gated by code the model does not control"*
  ([Unite.AI](https://www.unite.ai/agentic-sre-how-self-healing-infrastructure-is-redefining-enterprise-aiops-in-2026/),
  [khimananda](https://khimananda.com/blog/guardrails-for-autonomous-ai-agents)). The architecture is
  right; the work is building the envelope.
- **A4/A5 is past where industry runs.** Surveys of deployed agentic systems put **L3 "conditional
  autonomy" as the 2026 production ceiling** ([Knight Institute](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1),
  [ASDLC](https://asdlc.io/concepts/levels-of-autonomy/)). Not a reason to stop — a reason the
  evidence machinery has to be **homegrown**, because there is nobody to copy at the top of the ladder.

## 2. Options, function by function

### F1 · The loop — **event-driven scripts; steal durable execution's pattern, not its runtime**

| Option | Verdict |
|---|---|
| Cron + scripts (today) | Batch-only; no signal between nightlies |
| **Webhook receiver + scoped capability dispatch** (SKY-004 Option B) | **CHOSEN — already decided, still right** |
| Durable-execution engine (Temporal / Restate / DBOS / Inngest) | **Reject the runtime, adopt the pattern** |
| Agent framework (LangGraph and kin) | Reject — the harness is bash, and that is a feature |

Durable execution's core idea is worth stealing wholesale: **separate the deterministic, replayable
outer loop from the non-deterministic inner calls** — the loop is code, every LLM call and tool
invocation is a recorded "activity", and a crashed run resumes from the record rather than restarting
([Reactify](https://www.reactify-solutions.com/articles/durable-ai-agents-2026),
[Inngest](https://www.inngest.com/blog/durable-execution-key-to-harnessing-ai-agents)). That is
already half-built here: `journal/` is an append-only episode log. Make it the **replay log** — every
capability run writes its steps, so a resumed session continues rather than re-derives.

Reject the engines themselves: Temporal's workflow history lives in **its own database**, which is
system-class state outside git — a direct §2a violation — plus a standing service and a large
paradigm. The pattern costs a convention; the runtime costs the rebuild law.

### F2 · Deterministic gates — **keep bash for the hard laws; add Conftest/Rego for structured artifacts**

| Option | Verdict |
|---|---|
| `check-invariants.sh` (bash + jq, today) | Keep — legible, fast, already trusted for the hard laws |
| **OPA / Rego via `conftest`** | **Adopt, narrowly** |
| Checkov / tfsec | Reject — opinionated *cloud* rulesets; wrong target |
| HashiCorp Sentinel | Reject — proprietary, and off the table on OpenTofu anyway |

`conftest` is a single binary that evaluates Rego against structured files, and **`tofu plan -json`
is identical to Terraform's**, so the whole policy ecosystem applies unchanged
([Coding Protocols](https://codingprotocols.com/blog/terraform-policy-as-code-opa-sentinel-checkov),
[Spacelift](https://spacelift.io/blog/open-policy-agent-opa-terraform)). Two targets earn it here:

1. **`tofu plan -json`** — today the widest-blast-radius actuator has *no machine gate between plan
   and apply*. A policy that fails any plan containing a `delete` action, or touching a VMID outside
   the pool set, is the exact "envelope the model does not control" the guardrail literature
   describes.
2. **`inventory/firewall/firewall.json`** — the firewall-rule validation Ali asked for. The
   config.xml mirror is already parsed to JSON, so the rules ("no any-any", "no rule sourcing from
   `ROLE_OPS_*` into a T3 target", "every rule carries a description") are Rego over data that
   already exists. No new access, no new collector.

Honest cost: **Rego is a new language** — real branching factor. Mitigate by keeping the policy set
small and testing it (`conftest verify`), and by not migrating the existing hard laws: bash already
enforces them and legibility beats uniformity.

### F3 · Verification + automatic rollback — **the biggest hole, and it is per-actuator**

ADR 0005 §3 is unforgiving here: a rollback must be automatic, tested in failure, and run by
something dumber than the agent. Auditing what exists:

| Actuator | Automatic rollback today | What A4 needs |
|---|---|---|
| **nix hosts** (deploy-rs) | ✅ **magic-rollback** — activation reverts if the host doesn't confirm | already passes |
| **OPNsense ruleset** | ✅ **free and unexpected**: OPNsense validates before activating and restores the previous ruleset if `pfctl` rejects it ([DeepWiki](https://deepwiki.com/opnsense/core/4.1-firewall-rules-and-packet-filtering)) | already passes — good news for a *validate/propose* firewall capability |
| **compose services** (Arcane) | ❌ converges from git, but does **not** roll back on health failure — a noted Arcane gap ([bitdoze](https://www.bitdoze.com/portainer-alternatives/)) | a health-gated wrapper: deploy → probe → on failure `git revert` + reconcile |
| **`tofu apply`** | ❌ none | bounded plan + apply-the-saved-plan + pre-apply guest snapshot; `destroy` checkpointed forever |
| **DNS records** (Technitium / Cloudflare) | ❌ none, but trivially reversible | write the prior value to a revert file before each change |

For compose the tempting move is switching platforms — **Komodo** does deterministic compose GitOps
with richer deploy handling ([guide](https://medium.com/@mohammadfalahat/komodo-gitops-for-docker-stacks-a-complete-production-grade-guide-e88ebf3ad845)).
**Don't.** A ~100-line health-gated wrapper *is* the dumb executor the test asks for, costs no
platform churn, and works the same way for every actuator. Keep Komodo as the fallback only if the
wrapper starts growing into a product.

**The rule to adopt:** no actuator reaches A4 without a **named rollback executor** — a column in the
actuator table, not a paragraph in a runbook.

### F4 · The proving ground — **`tofu test` as the cheap tier, an ephemeral pool as the real one; skip Terratest**

| Option | Verdict |
|---|---|
| **`tofu test` / `.tofutest.hcl`** (native since 1.6) | **Adopt** — always-on cheap tier, no new language |
| **Ephemeral replica pool** (SKY-017 P2) | **Adopt** — the tier that produces actual evidence |
| Terratest (Go) | **Skip** — a new language and toolchain for one purpose |
| Permanent staging lab | Rejected in SKY-017 §2 — a second blast radius that drifts |

Terratest is the industry default for real-provisioning tests and does clean up even on failure
([envzero](https://www.envzero.com/blog/terratest-vs-terraform-opentofu-test-in-depth-comparison)),
but the assertions Skynet needs are "did the guest come up, does the service answer, does inventory
match" — bash and jq against the collectors that are already trusted. Writing Go to assert what
`collect-*.sh` already reports would add a language to save nothing. Worth internalising the honest
industry cost of this tier — *15–45 minutes of CI and a dedicated test account* — as the reason to
buy the cheap tier first and rehearse only what is being graduated.

### F5 · Adversarial review — **a second cold session; the AI-SRE products are Kubernetes-shaped**

| Option | Verdict |
|---|---|
| **Second cold agent session, different engine** | **Adopt** — the agent-agnostic contract was built for this |
| HolmesGPT | Reject as a product; steal one idea |
| k8sgpt | Reject — Kubernetes-only by construction |
| Commercial agentic-SRE platforms | Reject — SaaS control plane, data egress, state you don't own |

`bin/ops` already swaps engines, so a reviewer session with no shared context, handed only the diff,
the constitution and the stated intent, costs a script. Cross-engine matters: two sessions of the
same model share failure modes.

The one genuinely stealable idea is HolmesGPT's: **ground the investigation in the runbooks you
already wrote**, rather than in a bespoke rule engine ([CNCF](https://www.cncf.io/blog/2026/01/07/holmesgpt-agentic-troubleshooting-built-for-the-cloud-native-era/)).
Skynet has engine-neutral runbooks and a recon toolkit already — the diagnosis-agent pattern is
mostly built here, it just isn't wired to an event.

### F6 · The track record — **nothing off the shelf; build it**

Every autonomy framework found is **descriptive** — a vocabulary for where a system sits, never an
instrument that measures it. There is no product that says "this capability has 14 clean rehearsals
and 6 clean supervised runs, promote it." That has to be built: a generated, `inventory/`-class
record refreshed nightly and rendered into the cold-boot digest, so the agent knows what it is
trusted with and the promotion PR links the evidence that bought it.

## 3. The recommended stack

| Function | Choice | Why it wins here | Cost |
|---|---|---|---|
| **F1 Loop** | Webhook receiver + capabilities; journal as replay log | Keeps all state in git; no standing engine | a convention |
| **F2 Gates** | bash for hard laws **+ conftest/Rego** on `tofu plan -json` and `firewall.json` | Closes the widest-blast-radius gap; enables the firewall-validation capability | one new language, kept small |
| **F3 Verify** | Per-actuator rollback executors; health-gated deploy wrapper | Satisfies ADR 0005 §3 without platform churn | ~100 lines + a table |
| **F4 Rehearse** | `tofu test` + ephemeral `ops-rehearsal` pool, bash assertions | Real evidence, no new language | a pool (dial move) + provisioning time |
| **F5 Review** | Second cold session, cross-engine | Nearly free; the contract already supports it | a script |
| **F6 Record** | Generated per-capability evidence in `inventory/` | Turns promotion into a measurement | a renderer |

Nothing on that list is a standing service, a SaaS dependency, or state outside git. That is the test
§0 set, and it is also why almost none of the market's answers survived it.

## 4. What this changes in SKY-017

- **P1** — the actuator table gains a **named rollback executor** column; the audit above is its first
  draft (deploy-rs ✅, OPNsense ✅, Arcane ❌, tofu ❌, DNS ❌).
- **P2** — `tofu test` as the cheap tier, explicitly **not** Terratest.
- **P3** — adds **conftest/Rego** over `tofu plan -json`, and specifies the compose health-gated
  wrapper as the first rollback executor built.
- **P5** — the firewall-validation capability is now concrete: Rego over `inventory/firewall/firewall.json`,
  proposing at A1, with OPNsense's own pre-activation validation as the rollback that would let it
  climb later.
- **New framing to carry into the directive**: the missing MAPE-K phase is **Analyze**, so SKY-004's
  drift work is not a parallel track — it is the prerequisite that makes everything in SKY-017
  measurable.

---
### Sources
- MAPE-K / autonomic computing with LLMs — [MAPER (SEAMS 2026)](https://conf.researchr.org/details/seams-2026/seams-2026-research-track/26/MAPER-Extending-MAPE-K-with-LLM-Based-Reasoning-to-Manage-Unanticipated-Situations-i) · [Vision of Autonomic Computing (arXiv)](https://arxiv.org/html/2407.14402) · [MAPE-K overview](https://www.emergentmind.com/topics/mape-k-loop)
- Agentic SRE / guardrails 2026 — [Unite.AI](https://www.unite.ai/agentic-sre-how-self-healing-infrastructure-is-redefining-enterprise-aiops-in-2026/) · [khimananda](https://khimananda.com/blog/guardrails-for-autonomous-ai-agents) · [Nova AIOps](https://novaaiops.com/self-healing-infrastructure)
- Autonomy levels — [Knight First Amendment Institute](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1) · [ASDLC L1–L5](https://asdlc.io/concepts/levels-of-autonomy/) · [2025 AI Agent Index (arXiv)](https://arxiv.org/pdf/2602.17753)
- Policy as code — [OPA/Conftest vs Sentinel vs Checkov (2026)](https://codingprotocols.com/blog/terraform-policy-as-code-opa-sentinel-checkov) · [Spacelift OPA + Terraform](https://spacelift.io/blog/open-policy-agent-opa-terraform)
- Durable execution — [Reactify 2026](https://www.reactify-solutions.com/articles/durable-ai-agents-2026) · [Inngest](https://www.inngest.com/blog/durable-execution-key-to-harnessing-ai-agents)
- Compose GitOps + rollback — [Portainer alternatives 2026 (Arcane/Komodo)](https://www.bitdoze.com/portainer-alternatives/) · [Komodo guide](https://medium.com/@mohammadfalahat/komodo-gitops-for-docker-stacks-a-complete-production-grade-guide-e88ebf3ad845)
- OPNsense ruleset validation/restore — [DeepWiki: firewall rules & packet filtering](https://deepwiki.com/opnsense/core/4.1-firewall-rules-and-packet-filtering)
- Infra testing — [Terratest vs tofu test](https://www.envzero.com/blog/terratest-vs-terraform-opentofu-test-in-depth-comparison) · [OpenTofu testing framework](https://oneuptime.com/blog/post/2026-03-20-opentofu-testing-framework/view)
- AI-SRE agents — [HolmesGPT (CNCF)](https://www.cncf.io/blog/2026/01/07/holmesgpt-agentic-troubleshooting-built-for-the-cloud-native-era/) · [Open-source AI SRE comparison 2026](https://dev.to/siddharth_singh_409bd5267/open-source-ai-sre-aurora-vs-holmesgpt-vs-k8sgpt-2026-5g26)
- Agent sandboxing / unattended safety — [Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents) · [Runtime verification for AI agents](https://thebackenddevelopers.substack.com/p/runtime-verification-for-ai-agents)
