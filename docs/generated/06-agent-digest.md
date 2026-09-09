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
- **SKY-025** (projects · in-progress · 5/24) — Rebuild the Skynet engine in Python
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Explicit durable follow-ups:**

- **P6b is the remaining same-phase work** (OPNsense live + offline mirror parsing); detail it after this PR merges. One fresh review covers the whole numbered P6 after both slices merge. — _2026-09-09 session_
- **Live boundary, unverified (no live reads this packet):** the committed `inventory/dns-zones.json` shows the root `""` Secondary zone returning `records: null`. Under P6a's stricter contract a null record list fails the whole DNS refresh. If live Technitium genuinely returns null for that secondary/root zone, live DNS collection would report unavailable and retain prior bytes — the honest F8 signal, but it may need a zone-type exclusion or query adjustment at the P6b/live transition. Recorded, not resolved here. — _2026-09-09 session_
- Restore the local worktree: `git stash pop` the stashed inventory/docs + `tofu-drift.txt` after leaving this branch. — _2026-09-09 session_
- Finish full source/installed validation, repeat packaged live observations, then publish the combined repair/acceptance PR and P6a DNS packet. No P6 implementation is part of this run. — _2026-09-09 session_
- Workstation/state/payload recovery remains unverified. No backup/restore/prune, Docker mutation, activation, timer/service, root grant or credential/pin change was performed. — _2026-09-09 session_
- After Ali merges this P5 FIX planning PR, use Terra High: `Read planning/prompts/execute.md and execute SKY-025 P5 fix.` After fix PR(s) merge, request fresh Astra Medium review of #223, #224 and all fixes. — _2026-09-09 session_
- Workstation/state/payload recovery and live endpoint parity remain unverified. No live PBS/Docker permission is released by the fix packet; no root/grant, activation, timer/service, credential/pin change, backup/restore/prune or payload/state action occurred. — _2026-09-09 session_
- Run packaged/flake/hook checks, regenerate routing views, publish P5b. After human merge, request one fresh Astra Medium review for P5a and P5b before P6. — _2026-09-09 session_

## 📓 Recent episodes

- **2026-09-09** · session · [[2026-09-09-session-sky-025-p6a-dns-python-collection|sky-025-p6a-dns-python-collection]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p5-reviewer-repairs-and-live-reads|SKY-025 P5 reviewer repairs and live reads]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p5-combined-independent-review|SKY-025 P5 combined independent review]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p5b-docker-inventory|SKY-025 P5b Docker inventory]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p5a-pbs-inventory|SKY-025 P5a PBS inventory]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p4-combined-independent-review|SKY-025 P4 combined independent review]]
- **2026-09-08** · session · [[2026-09-08-session-sky-025-p4b-operate-token-acl-snapshots|SKY-025 P4b operate-token ACL snapshots]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
