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

- **P7a Omada (Terra High) is the sole released executable packet** (directive §5); P7b certs/routes and P7c recon are same-phase continuations, and one fresh review covers all P7 before P8. — _2026-09-09 session_
- **P6c + this review-fix await human merge** (PR #231 + the review-fix PR); once merged, the offline `config.xml` firewall inventory path is fully retired and the live OPNsense API is the sole source. — _2026-09-09 session_
- **Five paused documentation suites remain manual** (obsidian-hygiene, documentation-drift, temporal-hygiene, repo-surface, hygiene); P24 must restore maintained replacements to hook + CI before the directive closes. — _2026-09-09 session_
- **Generated agent-context surfaces (06-agent-digest, 07-context-map) were regenerated this session** to clear stale P6-in-progress/firewall context; they refresh from journal + planning, never hand-edited. — _2026-09-09 session_
- **Accepted progress is 6/24** (P6 accepted via #229); P7 has not started — never advance a numbered phase without its independent acceptance. — _2026-09-09 session_
- **Workstation/state/payload recovery and live endpoint parity remain unverified** across the overhaul; no live/production read or write, root, grant or credential change occurred this session. — _2026-09-09 session_
- Complete OPNsense repair/live retest, full installed/source checks and review publication. — _2026-09-09 session_
- No production inventory replacement, timer/service change, activation, root session, credential/pin change, zone write or firewall write occurred. The tests used disposable outputs; workstation/state/payload recovery remains unverified. — _2026-09-09 session_

## 📓 Recent episodes

- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6c-review-fix-regenerate-stale-agent-and-planning-context|sky-025 p6c review-fix regenerate stale agent and planning context]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6c-remove-offline-firewall-inventory-path|sky-025 p6c remove offline firewall inventory path]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6-combined-review-and-live-reads|SKY-025 P6 combined review and live reads]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6b-ii-opnsense-offline-mirror-parser|sky-025-p6b-ii-opnsense-offline-mirror-parser]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6b-opnsense-live-python-collection|sky-025-p6b-opnsense-live-python-collection]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6a-dns-python-collection|sky-025-p6a-dns-python-collection]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p5-reviewer-repairs-and-live-reads|SKY-025 P5 reviewer repairs and live reads]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
