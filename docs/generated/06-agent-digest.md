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
- **SKY-025** (projects · in-progress · 2/24) — Rebuild the Skynet engine in Python
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Explicit durable follow-ups:**

- After Ali merges P3b, one fresh Astra Medium review must cover all P3 implementation: #215 and the P3b PR. P4 is not authorized; accepted progress remains 2/24. — _2026-09-08 session_
- Before using the merged default path live, the map's independent workstation/state/payload recovery evidence remains required and unverified. No production API parity, recovery drill, credentials, profile install, root grant, host activation or timer/service change is claimed. — _2026-09-08 session_
- Restore maintained documentation/style/context checks in hook and CI before completing SKY-025; obsolete checks need an explicit disposition. The user-authorized pause is temporary. — _2026-09-08 session_
- After Ali merges PR #215, continue P3 by detailing and executing P3b within its integration, freshness and live/recovery boundaries. Request a fresh Astra Medium full P3/G2 review only after P3b completes and all P3 implementation PRs merge. Earlier P3a-only review handoffs are superseded by this correction; accepted numbered progress remains 2/24. — _2026-09-07 session_
- After Ali merges PR #215, start a fresh Astra Medium session: Read planning/prompts/review.md and review SKY-025 implementation PR https://github.com/aliammar03/skynet/pull/215. P3b remains unreleased. The earlier budget-pruning follow-up is satisfied by Ali's approval. — _2026-09-07 session_
- Resolve the current-authority budget with a bounded authorized follow-up before P3a can be accepted; at least 6,075 bytes plus headroom need removal, or an explicit budget policy decision. After Ali merges implementation, use a fresh Astra Medium task with planning/prompts/review.md. P3a is incomplete, accepted progress remains 2/24, and P3b's default-caller/freshness packet is not released. No real remote TLS/API parity, recovery rehearsal, host activation or live data freshness was verified here. — _2026-09-07 session_
- After Ali merges this review/planning PR, execute SKY-025 P3a in a fresh Astra Medium session using planning/prompts/execute.md. P3b and the map's live/recovery evidence remain unreleased. P2's merge/review prerequisite from the earlier journal is now satisfied; that episode stays append-only. — _2026-09-07 session_
- Ali merges the authored P2 implementation PR, then a fresh Astra Medium session reviews that merged result with `planning/prompts/review.md`; P3 is not authorized before that acceptance. — _2026-09-07 session_

## 📓 Recent episodes

- **2026-09-08** · session · [[2026-09-08-session-sky-025-p3b-default-collection-and-freshness|SKY-025 P3b default collection and freshness]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-full-phase-review-boundary|SKY-025 full phase review boundary]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-p3a-context-budget-approval|SKY-025 P3a context budget approval]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-p3a-isolated-core-collector|SKY-025 P3a isolated core collector]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-p2-independent-review|SKY-025 P2 independent review]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-p2-package-local-cli|SKY-025 P2 package local CLI]]
- **2026-09-07** · session · [[2026-09-07-session-sky-025-p1-independent-review|SKY-025 P1 independent review]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
