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
- **SKY-018** (projects · in-progress · 6/12) — Eight-layer reconciliation: entity spine, the Analyze phase, and the verification toolchain
- **SKY-020** (projects · in-progress · 1/6) — Firewall-as-code — OPNsense config to T2 via OpenTofu
- **SKY-023** (projects · in-progress · 10/10) — Eliminate documentation drift and shrink operational context
- **SKY-024** (projects · in-progress · 4/6) — tofu declares managed core guests — API-driven CT/VM lifecycle, no node SSH
- **SKY-025** (projects · in-progress · 1/24) — Rebuild the Skynet engine in Python
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Explicit durable follow-ups:**

- Ali merges the authored P2 implementation PR, then a fresh Astra Medium session reviews that merged result with `planning/prompts/review.md`; P3 is not authorized before that acceptance. — _2026-09-07 session_
- After Ali merges the review/planning PR, execute SKY-025 P2 in a fresh Terra High task with `planning/prompts/execute.md`. P1's earlier journal merge/review prerequisite is satisfied by this review; historical entry remains append-only. The map's live/recovery blockers remain open. — _2026-09-07 session_
- Human merge of the Phase 1 implementation PR, then fresh Astra Medium G1 review. Keep accepted progress at 0 until that reviewer accepts; only its human-merged next packet releases Phase 2. — _2026-09-07 session_
- Map explicitly blocks affected live phases on Arcane commands/revisions, remote host-local backup installs/units/OS, and independent workstation/kit/state/payload recovery checks. Unknown remote state is not evidence that callers are absent. Nothing is stopped to restore in P1. — _2026-09-07 session_
- _75 historical episode(s) have unclassified follow-ups; status unknown, not promoted as current work._

## 📓 Recent episodes

- **2026-09-07** · session · [[2026-09-07-session-sky-025-p2-package-local-cli|SKY-025 P2 package local CLI]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-p1-independent-review|SKY-025 P1 independent review]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-p1-repository-map-and-routing|SKY-025 P1 repository map and routing]]
- **2026-09-06** · session · [[2026-09-06-session-sky-025-phase-handoffs|Add SKY-025 execute and review handoffs]]
- **2026-09-06** · session · [[2026-09-06-session-sky-023-phase-10-lxc-base-template-upload|SKY-023 Phase 10 lxc-base template upload]]
- **2026-09-06** · session · [[2026-09-06-session-sky-023-phase-10-t1-classifier-and-base-build-checkpoint|SKY-023 Phase 10 T1 classifier and base build checkpoint]]
- **2026-09-06** · session · [[2026-09-06-session-sky-023-phase-9-hygiene-close-out|SKY-023 Phase 9 hygiene close-out]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
