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
- **SKY-025** (projects · in-progress · 4/24) — Rebuild the Skynet engine in Python
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Explicit durable follow-ups:**

- Run packaged/flake/hook checks, regenerate routing views, publish P5b. After human merge, request one fresh Astra Medium review for P5a and P5b before P6. — _2026-09-09 session_
- Regenerated digest, context map and roadmap after this entry. Commit, push and open the P5a PR. After Ali merges it, detail only P5b Docker; review both P5 slices together before P6. — _2026-09-09 session_
- After Ali merges this P4 ACCEPT planning PR, run a fresh Terra High session: `Read planning/prompts/execute.md and execute SKY-025 P5a.` — _2026-09-09 session_
- Workstation access, state/payload recovery, other endpoint parity and host activation remain unverified. Five paused documentation suites were not run or counted as passing; restore maintained replacements by P24. P4 live authorization does not authorize PBS/Docker execution. — _2026-09-09 session_
- Run full checks, regenerate digest/context, commit/push/open the P4b PR. After Ali merges it, request one fresh Astra Medium review covering both P4 slices before P5. — _2026-09-08 session_
- After this P4a PR is human-merged, execute only P4b: both ACL snapshots, operate-token self-introspection, paired ACL freshness and removal of their shell implementation; then obtain one fresh Astra Medium review for all of P4. — _2026-09-08 session_
- The map's live API parity, independent workstation access, state/payload recovery, and first live transition prerequisites remain unverified. — _2026-09-08 session_
- After Ali merges this credential-fix/P4 packet PR, execute SKY-025 §5 Phase 4a with Terra High via planning/prompts/execute.md. No additional P3 review round is required; accepted progress is 3/24. — _2026-09-08 session_

## 📓 Recent episodes

- **2026-09-09** · session · [[2026-09-09-session-sky-025-p5b-docker-inventory|SKY-025 P5b Docker inventory]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p5a-pbs-inventory|SKY-025 P5a PBS inventory]]
- **2026-09-09** · session · [[2026-09-09-session-sky-025-p4-combined-independent-review|SKY-025 P4 combined independent review]]
- **2026-09-08** · session · [[2026-09-08-session-sky-025-p4b-operate-token-acl-snapshots|SKY-025 P4b operate-token ACL snapshots]]
- **2026-09-08** · incident · [[2026-09-08-incident-sky-025-p4a-default-path-test-scope-breach|SKY-025 P4a default-path test scope breach]]
- **2026-09-08** · session · [[2026-09-08-session-sky-025-p4a-network-observations|SKY-025 P4a network observations]]
- **2026-09-08** · session · [[2026-09-08-session-sky-025-p3-combined-re-review|SKY-025 P3 combined re-review]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
