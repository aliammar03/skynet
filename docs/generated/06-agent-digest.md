---
title: Agent Digest
author: skynet-ops (render-digest.sh)
tags: [skynet, generated, agent, digest, cold-boot]
---

# Skynet — Agent Digest

A fresh session orients here: the settled **decisions** not to relitigate, the **open
threads** still in flight, and the most **recent episodes**. Facts and pointers only —
follow a link for the full story; distill episodes at read time, never in this file.

## 🧷 Recent decisions

- **[[0006-opnsense-read-is-t1-write-stays-t3|ADR 0006]]** — OPNsense tiered: read+diagnostics T1, config T2 (PR-gated via tofu), self-leash & reboot T3 · accepted · 2026-09-01
- **[[0005-full-agent-control-as-terminal-goal|ADR 0005]]** — Full agent control is the terminal goal; autonomy is earned, reversible, and never self-granted · accepted · 2026-08-28
- **[[0004-auto-merge-generated-only-nightly-prs|ADR 0004]]** — Auto-merge generated-only nightly PRs · accepted · 2026-08-20
- **[[0003-ambiguity-layering-and-format-follows-enforcement|ADR 0003]]** — Ambiguity-tolerance layering; format follows enforcement · accepted · 2026-08-18
- **[[0002-append-only-episodic-journal|ADR 0002]]** — Append-only episodic journal · accepted · 2026-08-17
- **[[0001-static-ip-addressing|ADR 0001]]** — Static IP addressing for Skynet guests · accepted · 2026-08-15 (revised 2026-08-17 — see *History*)

## 🧵 Open threads

**Directives in flight** (not done/abandoned):

- **SKY-005** (projects · in-progress · 2/3) — Imperative ops discipline: recon toolkit, diagnosis library, lab bench
- **SKY-006** (projects · in-progress · 2/3) — Agent episodic memory: journal + retrieval
- **SKY-008** (projects · active · 3/3) — OpenTofu provisioning layer: VM and CT lifecycle plus DNS
- **SKY-018** (projects · in-progress · 6/12) — Eight-layer reconciliation: entity spine, the Analyze phase, and the verification toolchain
- **SKY-020** (projects · in-progress · 1/6) — Firewall-as-code — OPNsense config to T2 via OpenTofu
- **SKY-023** (projects · in-progress · 3/4) — Eliminate documentation drift and shrink operational context
- **SKY-024** (projects · in-progress · 4/6) — tofu declares managed core guests — API-driven CT/VM lifecycle, no node SSH
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Loose ends from recent episodes** (the journal's own open-thread bullets, verbatim):

- Phase 1 remains T1 repository remediation. Provider-root/state separation for plan creation and a failure-tested automatic inverse for newly created guests remain future work; neither is claimed as A4-ready. — _2026-09-05 session          # session | incident | decision_
- PR #185 needs normal human review, CI confirmation, and merge. The agent must not merge it. — _2026-09-05 session          # session | incident | decision_
- Phase 3: split the publishing monolith and make all runbooks task-shaped. — _2026-09-05 session          # session | incident | decision_
- The directive references `[[SKY-023-progress]]`, but no repository-backed progress-memory file exists. This raw close-out episode is the durable repo record for resumption. — _2026-09-05 session          # session | incident | decision_
- Ali reviews and merges PR #185. Phase 2 starts only after that merge. — _2026-09-05 session          # session | incident | decision_
- Human-review and merge the Phase 1 PR; the agent does not merge authored work. — _2026-09-05 session          # session | incident | decision_
- Phase 2 may start only after Phase 1 merges. It owns constitution/spoke pruning and size targets; no Phase 2 pruning was performed here. — _2026-09-05 session          # session | incident | decision_
- SKY-020 still owns the OPNsense provider, write credential, policy gate, apply, and rollback proof. — _2026-09-05 session          # session | incident | decision_

## 📓 Recent episodes

- **2026-09-05** · session          # session | incident | decision · [[2026-09-05-session-sky-023-phase-1-audit-remediation|SKY-023 Phase 1 audit remediation]]
- **2026-09-05** · session          # session | incident | decision · [[2026-09-05-session-sky-023-p2-close-out|SKY-023 P2 close-out]]
- **2026-09-05** · session          # session | incident | decision · [[2026-09-05-session-sky-023-p1-pr-integration|SKY-023 P1 PR integration]]
- **2026-09-05** · session          # session | incident | decision · [[2026-09-05-session-sky-023-p1-close-out|SKY-023 P1 close-out]]
- **2026-09-05** · session · [[2026-09-05-session-nightly-2026-09-05|nightly 2026-09-05]]
- **2026-09-05** · decision          # session | incident | decision · [[2026-09-05-decision-sky-023-p1-create-blocker-correction|SKY-023 P1 create blocker correction]]
- **2026-09-04** · session          # session | incident | decision · [[2026-09-04-session-sky-023-p1-truth-reconciliation|SKY-023 P1 truth reconciliation]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
