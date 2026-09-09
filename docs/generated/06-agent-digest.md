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
- **SKY-025** (projects · in-progress · 6/24) — Rebuild the Skynet engine in Python
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Explicit durable follow-ups:**

- Open the bounded P7 fix PR, then await human merge and a fresh review of the complete P7 merged result. Accepted progress remains 6/24. — _2026-09-10 session_
- P7c must be human-merged, then a fresh review covers P7a #235, P7b #236 and this P7c PR. Accepted progress remains 6/24 until that reviewer accepts the complete numbered phase. — _2026-09-09 session_
- P7b must be human-merged before the lead details P7c recon. P7 remains unaccepted at 6/24; P7c and the independent merged-result review are still required. — _2026-09-09 session_
- P7b certificate probes and static Caddy route parsing remain the next same-phase slice after this authored PR is human-merged; P7c recon then follows. P7 has no independent acceptance until every slice is merged and reviewed together. — _2026-09-09 session_
- Live Omada authentication/read, production inventory replacement, timer/service activation, credential/pin change and recovery checks remain unperformed. — _2026-09-09 session_
- **P7a Omada (Terra High) is the sole released executable packet** (directive §5); P7b certs/routes and P7c recon are same-phase continuations, and one fresh review covers all P7 before P8. — _2026-09-09 session_
- **Accepted SKY-025 progress is 6/24**; P7 has not started — never advance a numbered phase without its independent acceptance. — _2026-09-09 session_
- **Offline `config.xml` firewall inventory parsing is retired** (P6c): the live OPNsense API (`src/skynet/opnsense.py`) is the sole firewall inventory source, and the `config.xml` git backup is DR-only — restored as configuration into OPNsense, never parsed into inventory. — _2026-09-09 session_

## 📓 Recent episodes

- **2026-09-10** · session · [[2026-09-10-session-sky-025-p7-route-and-recon-review-fixes|SKY-025 P7 route and recon review fixes]]
- **2026-09-09** · incident · [[2026-09-09-incident-sky-025-p7c-shell-only-unavailable-path|SKY-025 P7c shell-only unavailable path]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p7c-bounded-python-reconnaissance|SKY-025 P7c bounded Python reconnaissance]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p7b-certificate-and-static-route-observations|SKY-025 P7b certificate and static route observations]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p7a-omada-python-collection|SKY-025 P7a Omada Python collection]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6c-digest-supersede-stale-await-merge-follow-up|sky-025 p6c digest supersede stale await-merge follow-up]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6c-review-fix-regenerate-stale-agent-and-planning-context|sky-025 p6c review-fix regenerate stale agent and planning context]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
