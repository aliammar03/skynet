---
title: Agent Digest
summary: Recent-activity, episodic, and open-thread retrieval view.
author: skynet-ops (skynet render digest)
tags: [skynet, generated, agent, digest, recent-activity, episodic]
---

# Skynet — Agent Digest

Use this view to retrieve recent **decisions**, **open threads**, and **recent episodes**.
Facts and pointers only — follow a link for the full story; distill episodes at read time,
never in this file. Normal fresh-session continuity starts with `agent_docs/` plus the active
directive; this generated page is optional recent-activity and episodic retrieval.

## 🧷 Recent decisions

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
- **SKY-025** (projects · in-progress · 9/24) — Rebuild the Skynet engine in Python
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Explicit durable follow-ups:**

- After SKY-025 finishes, Ali reviews the repository and authors one coherent replacement test/CI architecture. — _2026-09-13 decision_
- PR #255 requires a fresh external review because the pre-embargo ACCEPT marker is stale. — _2026-09-13 decision_
- Require green focused lifecycle tests and full repository CI on the repaired #253 head. — _2026-09-12 session_
- Run a new fresh external review of open PR #253. The previous acceptance marker must not be reused. — _2026-09-12 session_
- On new ACCEPT, Ali returns to the original implementation session with only `accepted`; Main reruns bounded same-PR closeout and final CI before handing #253 back for one human merge. — _2026-09-12 session_
- The current installed Home Manager generation still reports `approval OnRequest`; the authored target must be human-merged and activated through the normal declarative path before the live user configuration changes. — _2026-09-10 session_
- After activation, run one fresh native-child smoke test, then continue SKY-026 Phase 5. — _2026-09-10 session_
- After activation, directly write and remove harmless probes in `.agents/` and `.codex/`; the current pre-merge session could verify their configuration contracts but not their live writes. — _2026-09-10 session_
- _11 historical episode(s) have unclassified follow-ups; status unknown, not promoted as current work._

## 📓 Recent episodes

- **2026-09-13** · session · [[2026-09-13-session-sky-025-p9-accepted-same-pr-closeout|SKY-025 P9 accepted same-PR closeout]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p9-gnu-ere-recall-review-fix|SKY-025 P9 GNU ERE recall review fix]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p9-implementation-ready|SKY-025 P9 implementation ready]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p8-accepted-same-pr-closeout|SKY-025 P8 accepted same-PR closeout]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p8-embargo-documentation-reconciliation|SKY-025 P8 embargo documentation reconciliation]]
- **2026-09-13** · decision · [[2026-09-13-decision-sky-025-repository-test-and-github-ci-embargo|SKY-025 repository test and GitHub CI embargo]]
- **2026-09-13** · session · [[2026-09-13-session-sky-025-p8-non-compose-label-review-fix|SKY-025 P8 non-Compose label review fix]]

---
_Human narrative: [[05-state-of-the-lab]] · on-demand load-cost map: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Recent-activity / episodic / open-thread retrieval view — generated by
> `skynet render digest` from ADRs + the journal + the roadmap. Do not hand-edit.
> Content-stable (diffs only on real change). Normal fresh-session continuity starts with
> `agent_docs/` plus the active directive; this page is optional retrieval.
