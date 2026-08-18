# ADR 0003 — Ambiguity-tolerance layering; format follows enforcement

- **Status:** accepted
- **Date:** 2026-08-18

## Context

A question kept recurring across the roadmap: should Skynet's system design itself be rewritten
"machine-readable" — invariants, tiers, and exclusions converted from prose to a schema — so the
agent interprets it less loosely? The instinct is understandable. Two of our best directives push
in adjacent directions: *shrink the always-loaded context* ([SKY-010](../../planning/projects/SKY-010-default-lean-context-load-on-demand.md))
and *push the declarative boundary down* ([SKY-007](../../planning/ideas/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md)
Nix, [SKY-008](../../planning/ideas/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md)
Tofu). Surely schematizing the constitution is more of the same good medicine?

Working it through surfaced the opposite conclusion, and a principle none of the existing
directives states outright.

**An LLM reads a schema with the same latitude it reads prose.** Converting an invariant from a
sentence to `never_pool: [5001]` buys *no additional rigor* if the only consumer is still the
agent — it interprets the YAML with exactly the freedom it interprets "VM 5001 never joins any
pool." Structure constrains a machine; it merely *suggests* to a mind that reasons in natural
language. So the format of a constraint is not what makes it binding.

What makes a constraint binding is **who enforces it**. Three of Skynet's invariants are already
rock-solid, and not one of them because of how it's written down:

- the signing CA private key lives on Ali's workstation ⇒ the agent *cannot* mint root — guaranteed
  by physics, not by policy or format;
- `git revert` → Arcane reconciles ⇒ rollback is deterministic because a non-LLM executor performs it;
- the render scripts are the only writer of `docs/generated/` and `inventory/` ⇒ "never hand-edit
  generated dirs" is structurally true, enforced by the pipeline, not by memory.

Set against those, the **blast-radius laws** are prose repeated across `AGENTS.md §6`,
`docs/system-design.md §2/§3`, and directive warnings — and enforced by *nothing but the agent
remembering them*: excluded guests (5001/635/837/2020) never joining a pool, the write blast radius
equalling the declared pool set, secrets never landing in plaintext. That gap grows dangerous the
instant [SKY-008](../../planning/ideas/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md)
can touch pool membership — pool membership *is* the blast-radius dial, so a mis-generated `tofu
apply` needs a dumb gate behind it that no amount of plausible reasoning can talk past.

## Decision

Adopt **ambiguity-tolerance layering** as the organizing principle for how Skynet represents
knowledge, and **format follows enforcement** as its operative rule.

**1. Sort every artifact by how much interpretation it can safely tolerate.** From least to most:

| Layer | Example artifacts | Tolerates interpretation? | Format & enforcement |
|---|---|---|---|
| **State** | `inventory/*.json`, firewall mirror | No | Data; *generated from* the world, deterministically diffed |
| **Constraints** | `invariants.json` (SKY-011 P2) | No | Authored data; read by a **deterministic gate** |
| **Provisioning** | Nix (SKY-007), Tofu (SKY-008) | No | Declarative code; a non-LLM executor applies it |
| **Procedures** | `runbooks/`, `scripts/`, `bin/` | A little | Engine-neutral markdown + bash; steps are literal |
| **Directives** | `planning/SKY-###` | Some | Structured prose; a plan a mind executes |
| **Judgment** | `docs/system-design.md`, ADRs, rationale | Fully — that's the point | Authored natural-language prose |

**2. Format follows enforcement.** Schematize a thing *only when a deterministic, non-LLM process
will consume the schema*. Machine-*enforced* below the line (state, constraints, provisioning);
natural-language *above* it (directives, judgment, rationale); a thin retrieval pipe between them
(SKY-010's context map + on-demand load). Structuring an upper-layer artifact for a lower-layer
reason — turning the constitution into YAML "for safety" — gains nothing and destroys the
human-legible law. It is the anti-pattern this ADR exists to forbid.

**3. Therefore, split by consumer.** The constitution, the ADRs, and all rationale **stay authored
prose** — their job is to *constrain judgment*, which is a natural-language act. What is genuinely
machine-checkable (excluded VMIDs, the declared pool set, secret patterns) is extracted into typed
data (`invariants.json`) that a script reads and fails a PR on. Same split the system already uses
for ADR-vs-constitution: the durable reasoning lives in an ADR, a one-paragraph pointer lives in the
constitution.

This is the spine that [SKY-004](../../planning/ideas/SKY-004-reactive-operations-event-driven-layer-drift-as-signal.md),
[SKY-006](../../planning/projects/SKY-006-agent-episodic-memory-journal-retrieval.md),
[SKY-007](../../planning/ideas/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md),
[SKY-008](../../planning/ideas/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md),
and [SKY-010](../../planning/projects/SKY-010-default-lean-context-load-on-demand.md) all silently
assume. Writing it down stops a future session from "helpfully" schematizing the constitution and
calling it safety — and tells the declarative-infra bets exactly *what* to schematize (the state and
constraints they generate or assert) and what to leave as prose (the judgment about whether to).

## Consequences

- **The gap gets closed, not papered over.** SKY-011 Phases 2–3 extract the machine-checkable hard
  laws into `invariants.json` and enforce them with `scripts/check-invariants.sh` wired into the
  git-hook/CI path — a deterministic gate that fails a bad PR, replacing "the agent remembering."
- **The constitution stays prose, on purpose.** No PR converts `system-design.md §2/§3` to a schema;
  §2 gains only a one-paragraph pointer to this doctrine. Rewriting law into data is now a named
  anti-pattern, not an open temptation.
- **The declarative bets have a rule to cite.** When SKY-007/008 ask "should this be code or prose?",
  the answer is mechanical: code if a non-LLM executor consumes it, prose if a mind does.
- **Rigor is traced to its real source.** We stop mistaking format for enforcement. A constraint is
  "rock solid" only once you can name the deterministic process that consumes it — physics, a
  reconciler, a pipeline, or a gate — never because it is written in YAML.

<!-- ADRs are amended IN PLACE, never superseded (docs/conventions/docs.md). When this decision
     changes — a correction or a full reversal — edit THIS file to state what's true now and add a
     dated line under a `## History` section; the git log holds the prior wording. -->
