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
- **SKY-008** (projects · active · 2/3) — OpenTofu provisioning layer: VM and CT lifecycle plus DNS
- **SKY-018** (projects · in-progress · 5/12) — Eight-layer reconciliation: entity spine, the Analyze phase, and the verification toolchain
- **SKY-020** (projects · in-progress · 1/6) — Firewall-as-code — OPNsense config to T2 via OpenTofu
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Loose ends from recent episodes** (the journal's own open-thread bullets, verbatim):

- Confirm the intended lifetime of `tofu-test.tdns.home.aliammar.net → 192.0.2.1` through the reviewed OpenTofu workflow. — _2026-09-02 session          # session | incident | decision_
- Confirm whether missing `project.env` files for `aiometadata` and `aiostreams` are intentional. — _2026-09-02 session          # session | incident | decision_
- PBS snapshot freshness, restic payloads, restore behavior, and the L5 Google Drive mirror remain unverified. — _2026-09-02 session          # session | incident | decision_
- **P2 next:** move the VLAN display-name map + reverse-proxy front-door alias set out of `render-docs.sh` into `lab.json`; add `entity_conventions` (VMID->IP law + declared exceptions) to `invariants.json`; add the 4th law to `check-invariants.sh` (every running entity mapped or excepted). arcane-manager, 101, 526, 999 must each be triaged (destroy / bring-in / declare) before the law can go enforcing rather than report-only. — _2026-09-01 session          # session | incident | decision_
- lab.json currently holds only `docker_hosts`; P2 owns the rest of its authored content. — _2026-09-01 session          # session | incident | decision_
- vhost + net classes have no collector yet (P5 Caddy routes, P4 network gear). — _2026-09-01 session          # session | incident | decision_
- Recent PBS snapshots and the L5 Google Drive mirror remain unverified by this run. — _2026-09-01 session          # session | incident | decision_
- Confirm whether the observed firewall removals and role-member reductions were intentional. — _2026-09-01 session_

## 📓 Recent episodes

- **2026-09-02** · session          # session | incident | decision · [[2026-09-02-session-nightly-2026-09-02|nightly 2026-09-02]]
- **2026-09-01** · session          # session | incident | decision · [[2026-09-01-session-sky-018-p1-first-entity-audit|SKY-018 P1 first entity audit]]
- **2026-09-01** · session          # session | incident | decision · [[2026-09-01-session-nightly-2026-09-01|nightly 2026-09-01]]
- **2026-09-01** · session · [[2026-09-01-session-nightly-2026-09-01-2350|nightly 2026-09-01 2350]]
- **2026-09-01** · session          # session | incident | decision · [[2026-09-01-session-nightly-2026-09-01-1805|nightly 2026-09-01 1805]]
- **2026-09-01** · session · [[2026-09-01-session-nightly-2026-09-01-1735-rerun|nightly 2026-09-01 1735 rerun]]
- **2026-09-01** · session          # session | incident | decision · [[2026-09-01-session-generated-docs-review-and-digest-stale-thread-fix|generated-docs review and digest stale-thread fix]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
