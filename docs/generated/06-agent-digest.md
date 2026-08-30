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

- **PBS (VMID 240) — 4 nights stopped as of tonight.** Needs a human decision: deliberate maintenance or an unplanned outage quietly starving the L5 PBS→Drive backup layer. Escalating the framing tonight since it's no longer a one-off flag. — _2026-08-30 session          # session | incident | decision_
- **Nightly PR backlog**: #113 (08-28) and #115 (08-29) are both open, unmerged, report-only/ generated-only — should be safe to merge and would stop `main` drifting further from the inventory's actual state. — _2026-08-30 session          # session | incident | decision_
- **VMID 999 still running, unexplained** — third observation in a row, probably benign (Ali comparing something against the old pre-NixOS box?) but still unconfirmed. — _2026-08-30 session          # session | incident | decision_
- From the 2026-08-28 entity-model decision journal entry (carried via the agent digest, not independently re-verified tonight): `10.10.100.35`'s ownership needs resolving before CT 1035 (caddy-dmz, stopped) gets destroyed — nine published apps depend on it; CT 526 (UniFi controller) is running and unmapped in DNS/reservations; `arcane-manager`'s GitOps-exception status is still Ali's call. — _2026-08-30 session          # session | incident | decision_
- SKY-008 P3 (DNS provider + declarative LXC import) still not started (per `planning/projects/SKY-008-*.md` status log — Phase 1+2 done both nodes, Phase 3 open). — _2026-08-30 session          # session | incident | decision_
- Core-node PBS CT 240 (`ops-managed`) is still stopped; network-node PBS CT 240 is running. The stopped core instance still needs a human decision. No guest-power action was taken. — _2026-08-30 session          # session | incident | decision_
- Legacy VMID 999 remains running and unexplained. No guest-power action was taken. — _2026-08-30 session          # session | incident | decision_
- The pre-existing uncommitted 2026-08-28 Jikan journal correction remains local and excluded from this nightly commit/PR. — _2026-08-30 session          # session | incident | decision_

## 📓 Recent episodes

- **2026-08-30** · session          # session | incident | decision · [[2026-08-30-session-nightly-2026-08-30|nightly 2026-08-30]]
- **2026-08-30** · session          # session | incident | decision · [[2026-08-30-session-nightly-2026-08-30-third-pass|nightly 2026-08-30 third pass]]
- **2026-08-30** · session          # session | incident | decision · [[2026-08-30-session-nightly-2026-08-30-second-pass|nightly 2026-08-30 second pass]]
- **2026-08-30** · session · [[2026-08-30-session-nightly-2026-08-30-fourth-pass|nightly 2026-08-30 fourth pass]]
- **2026-08-29** · session          # session | incident | decision · [[2026-08-29-session-nightly-2026-08-29|nightly 2026-08-29]]
- **2026-08-28** · session          # session | incident | decision · [[2026-08-28-session-seed-jikan-anime-index-for-aiometadata|seed jikan anime index for aiometadata]]
- **2026-08-28** · session          # session | incident | decision · [[2026-08-28-session-nightly-2026-08-28|nightly 2026-08-28]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
