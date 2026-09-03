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
- **SKY-008** (projects · active · 3/3) — OpenTofu provisioning layer: VM and CT lifecycle plus DNS
- **SKY-018** (projects · in-progress · 6/12) — Eight-layer reconciliation: entity spine, the Analyze phase, and the verification toolchain
- **SKY-020** (projects · in-progress · 1/6) — Firewall-as-code — OPNsense config to T2 via OpenTofu
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Loose ends from recent episodes** (the journal's own open-thread bullets, verbatim):

- ⚠ pve-snapshot.sh needs the OPERATE token (PVE_OPERATE_TOKEN); standing proxmox-<node>.env only has the readonly token. Confirm it's materialized before any live `tofu-apply.sh`. Until then tofu-apply fails closed (can't snapshot → won't apply) — correct, but means no live tofu rollback demo yet. — _2026-09-03 session          # session | incident | decision_
- P6 wrappers are opt-in and not yet wired into bin/ops / the nightly (report-only). That wiring is a SKY-017 autonomy-promotion step, not P6. — _2026-09-03 session          # session | incident | decision_
- NEXT: P7 (conftest/Rego over `tofu plan`) — explicitly NOT started this session. — _2026-09-03 session          # session | incident | decision_
- Confirm whether VMID 10015's reboot was planned. — _2026-09-03 session_
- Check `10.10.80.37` if the identity host should be continuously reachable. — _2026-09-03 session_
- Confirm whether missing `project.env` files for `aiometadata` and `aiostreams` are intentional, and why `scripts/envsync.sh` exits 1 after those skips. — _2026-09-03 session_
- Exercise a restore, verify restic and the L5 Google Drive mirror, and review the 11 PBS groups without a verification state. — _2026-09-03 session_
- **Ali action:** delete the leftover live record `tofu-test.tdns.home.aliammar.net A 192.0.2.1`, and add record-delete to the scoped Technitium token (the DNS phase needs it for `tofu destroy`). — _2026-09-02 session          # session | incident | decision_

## 📓 Recent episodes

- **2026-09-03** · session          # session | incident | decision · [[2026-09-03-session-sky-018-p6-l7-rollback-executors|SKY-018 P6 — L7 rollback executors]]
- **2026-09-03** · session · [[2026-09-03-session-nightly-2026-09-03|nightly 2026-09-03]]
- **2026-09-02** · session          # session | incident | decision · [[2026-09-02-session-sky-008-p3-ct-240-import-dns-provider-blocked|SKY-008 P3 — CT 240 import + DNS provider blocked]]
- **2026-09-02** · session          # session | incident | decision · [[2026-09-02-session-nightly-2026-09-02|nightly 2026-09-02]]
- **2026-09-01** · session          # session | incident | decision · [[2026-09-01-session-sky-018-p1-first-entity-audit|SKY-018 P1 first entity audit]]
- **2026-09-01** · session          # session | incident | decision · [[2026-09-01-session-nightly-2026-09-01|nightly 2026-09-01]]
- **2026-09-01** · session · [[2026-09-01-session-nightly-2026-09-01-2350|nightly 2026-09-01 2350]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
