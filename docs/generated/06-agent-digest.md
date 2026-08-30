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

- **[[0005-full-agent-control-as-terminal-goal|ADR 0005]]** — Full agent control is the terminal goal; autonomy is earned, reversible, and never self-granted · accepted · 2026-08-28
- **[[0004-auto-merge-generated-only-nightly-prs|ADR 0004]]** — Auto-merge generated-only nightly PRs · accepted · 2026-08-20
- **[[0003-ambiguity-layering-and-format-follows-enforcement|ADR 0003]]** — Ambiguity-tolerance layering; format follows enforcement · accepted · 2026-08-18
- **[[0002-append-only-episodic-journal|ADR 0002]]** — Append-only episodic journal · accepted · 2026-08-17
- **[[0001-static-ip-addressing|ADR 0001]]** — Static IP addressing for Skynet guests · accepted · 2026-08-15 (revised 2026-08-17 — see *History*)

## 🧵 Open threads

**Directives in flight** (not done/abandoned):

- **SKY-005** (projects · in-progress · 2/3) — Imperative ops discipline: recon toolkit, diagnosis library, lab bench
- **SKY-006** (projects · in-progress · 2/3) — Agent episodic memory: journal + retrieval
- **SKY-008** (projects · active · 2/3) — OpenTofu provisioning layer: VM and CT lifecycle plus DNS
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-018** (ideas · draft) — Eight-layer reconciliation: entity spine, the Analyze phase, and the verification toolchain

**Loose ends from recent episodes** (the journal's own open-thread bullets, verbatim):

- Core-node PBS CT 240 (`ops-managed`) is still stopped; network-node PBS CT 240 is running. The stopped core instance still needs a human decision. No guest-power action was taken. — _2026-08-30 session          # session | incident | decision_
- Legacy VMID 999 remains running and unexplained. No guest-power action was taken. — _2026-08-30 session          # session | incident | decision_
- The pre-existing uncommitted 2026-08-28 Jikan journal correction remains local and excluded from this nightly commit/PR. — _2026-08-30 session          # session | incident | decision_
- SKY-008 Phase 3 remains open according to the generated digest. — _2026-08-30 session          # session | incident | decision_
- **PBS CT 240 (core, `ops-managed`) — still stopped**, last running 2026-08-27. No change since #116. The network-node PBS is up, so this is not a total backup outage, but the L5 PBS-datastore→Drive mirror for the core instance has had nothing fresh to mirror for days. Still needs a human call: deliberate maintenance vs unplanned stop. — _2026-08-30 session          # session | incident | decision_
- **Nightly-PR backlog: CLEARED.** #113 / #115 / #116 all on `main`; `main` now tracks reality. — _2026-08-30 session          # session | incident | decision_
- **VMID 999 still running, unexplained** — carried forward, not worsening. — _2026-08-30 session          # session | incident | decision_
- From the 2026-08-28 entity-model decision (via the agent digest, not re-verified tonight): `10.10.100.35` ownership must be resolved before CT 1035 (caddy-dmz, stopped) is destroyed — nine published apps depend on it; the record is still being queried (see dns diff above). CT 526 (UniFi controller, network node) running and unmapped in DNS/reservations. `arcane-manager` GitOps-exception status still Ali's call. — _2026-08-30 session          # session | incident | decision_

## 📓 Recent episodes

- **2026-08-30** · session          # session | incident | decision · [[2026-08-30-session-nightly-2026-08-30-third-pass|nightly 2026-08-30 third pass]]
- **2026-08-30** · session          # session | incident | decision · [[2026-08-30-session-nightly-2026-08-30-second-pass|nightly 2026-08-30 second pass]]
- **2026-08-30** · session          # session | incident | decision · [[2026-08-30-session-nightly-2026-08-30|nightly 2026-08-30]]
- **2026-08-29** · session          # session | incident | decision · [[2026-08-29-session-nightly-2026-08-29|nightly 2026-08-29]]
- **2026-08-28** · session          # session | incident | decision · [[2026-08-28-session-seed-jikan-anime-index-for-aiometadata|seed jikan anime index for aiometadata]]
- **2026-08-28** · session          # session | incident | decision · [[2026-08-28-session-nightly-2026-08-28|nightly 2026-08-28]]
- **2026-08-28** · decision · [[2026-08-28-decision-entity-model-and-naming-convention|Entity model (five classes) and the final naming convention]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
