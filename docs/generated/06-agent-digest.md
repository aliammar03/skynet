---
title: Agent Digest
summary: Recent-activity, episodic, and open-thread retrieval view.
author: skynet-ops (skynet render digest)
tags: [skynet, generated, agent, digest, recent-activity, episodic]
---

# Skynet — Agent Digest

Use this view to retrieve recent **decisions**, **open threads**, and **recent episodes**.
Facts and pointers only — follow a link for the full story; distill episodes at read time,
never in this file. Normal fresh-session continuity starts with `AGENTS.md` plus the active
directive; this generated page is optional recent-activity and episodic retrieval.

## 🧷 Recent decisions

- **[[0007-local-tests-review-tiers-agent-agnostic-construction|ADR 0007]]** — Local tests, Light/Full review tiers, agent-agnostic construction · accepted · 2026-09-23
- **[[0006-opnsense-read-is-t1-write-stays-t3|ADR 0006]]** — OPNsense tiered: read+diagnostics T1, config T2 (PR-gated via tofu), self-leash & reboot T3 · accepted · 2026-09-01
- **[[0005-full-agent-control-as-terminal-goal|ADR 0005]]** — Full agent control is the terminal goal; autonomy is earned, reversible, and never self-granted · accepted · 2026-08-28
- **[[0004-auto-merge-generated-only-nightly-prs|ADR 0004]]** — Auto-merge generated-only nightly PRs · suspended during the SKY-025 test/CI embargo · 2026-08-20
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
- **SKY-025** (projects · in-progress · 10/17) — Rebuild the Skynet engine in Python
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Explicit durable follow-ups:**

- Ali: add grant-root deny/ask rules for opencode in nix/home/aliammar.nix, then list it in invariants.json construction.engines. — _2026-09-23 decision_
- Nix changes (devshell + base python3.withPackages pytest) were not built in the authoring container (no nix); verify with `nix develop` and a rebuild on the ops VM. — _2026-09-23 decision_
- _94 historical episode(s) have unclassified follow-ups; status unknown, not promoted as current work._

## 📓 Recent episodes

- **2026-09-23** · decision · [[2026-09-23-decision-process-overhaul-tests-back-review-tiers-agent-agnostic-construction|Process overhaul: tests back, review tiers, agent-agnostic construction]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p10-accepted-same-pr-closeout|SKY-025 P10 accepted same-PR closeout]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p10-revision-identity-review-fix|SKY-025 P10 revision identity review fix]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p10-implementation-ready|SKY-025 P10 implementation ready]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p9-accepted-same-pr-closeout|SKY-025 P9 accepted same-PR closeout]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p9-gnu-ere-recall-review-fix|SKY-025 P9 GNU ERE recall review fix]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p9-implementation-ready|SKY-025 P9 implementation ready]]

---
_Human narrative: [[05-state-of-the-lab]] · on-demand load-cost map: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Recent-activity / episodic / open-thread retrieval view — generated by
> `skynet render digest` from ADRs + the journal + the roadmap. Do not hand-edit.
> Content-stable (diffs only on real change). Normal fresh-session continuity starts with
> `AGENTS.md` plus the active directive; this page is optional retrieval.
