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
- **SKY-023** (projects · in-progress · 1/4) — Eliminate documentation drift and shrink operational context
- **SKY-024** (projects · in-progress · 3/6) — tofu declares all pool guests — API-driven CT/VM lifecycle, no node SSH
- **SKY-002** (ideas · draft) — Ongoing backup strategy for CT 240 (PBS host)
- **SKY-004** (ideas · draft) — Reactive operations: event-driven layer + drift-as-signal
- **SKY-012** (ideas · draft) — Runbooks as executable capabilities
- **SKY-015** (ideas · draft) — Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
- **SKY-016** (ideas · draft) — Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
- **SKY-017** (ideas · draft) — The road to full agent control: verification, proving ground, and an evidence-earned ratchet
- **SKY-019** (ideas · draft) — Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely

**Loose ends from recent episodes** (the journal's own open-thread bullets, verbatim):

- Human-review and merge the Phase 1 PR; the agent does not merge authored work. — _2026-09-05 session          # session | incident | decision_
- Phase 2 may start only after Phase 1 merges. It owns constitution/spoke pruning and size targets; no Phase 2 pruning was performed here. — _2026-09-05 session          # session | incident | decision_
- SKY-020 still owns the OPNsense provider, write credential, policy gate, apply, and rollback proof. — _2026-09-05 session          # session | incident | decision_
- Design failure-tested rollback executors for non-guest tofu writes and new-guest creates before either capability can reach A4; add live-Caddy-versus-git drift detection separately. — _2026-09-05 session          # session | incident | decision_
- Phase 1 was paused before close-out. A delegated final review found six remaining corrections: DNS deletion rollback must not claim `tofu-apply.sh` can apply deletes; non-guest OpenTofu writes have no automatic snapshot rollback; the OPNsense write actuator is pending SKY-020; nightly route collection does not compare live Caddy config with git; Obsidian is the own-auth reference while calibre is the proven forward-auth reference; and the forward-auth runbook must put the merged PR before Authentik API mutations. — _2026-09-04 session          # session | incident | decision_
- Resume Phase 1 on `phase/sky-023-p1`. Apply those corrections, including the related comments in `scripts/gitops-deploy.sh`, `tofu/cloudflare-dns.tf`, and `tofu/pool-cts.tf`; clarify that the core credential can technically reach Unraid 2020's envelope although policy forbids destructive use. — _2026-09-04 session          # session | incident | decision_
- Re-run owning generators sequentially, then the full invariant/test/syntax/link suite and `git diff --check`. Only then mark Phase 1 complete and open its human-merged PR. — _2026-09-04 session          # session | incident | decision_
- Phase 2 remains out of scope until the Phase 1 PR is reviewed and merged. — _2026-09-04 session          # session | incident | decision_

## 📓 Recent episodes

- **2026-09-05** · session          # session | incident | decision · [[2026-09-05-session-sky-023-p1-close-out|SKY-023 P1 close-out]]
- **2026-09-04** · session          # session | incident | decision · [[2026-09-04-session-sky-023-p1-truth-reconciliation|SKY-023 P1 truth reconciliation]]
- **2026-09-04** · session · [[2026-09-04-session-sky-022-p6-proactive-cost-aware-delegation|SKY-022 P6 — proactive cost-aware delegation]]
- **2026-09-04** · session · [[2026-09-04-session-sky-022-p5-five-run-foreman-dogfood|SKY-022 P5 — five-run foreman dogfood]]
- **2026-09-04** · session          # session | incident | decision · [[2026-09-04-session-sky-022-p4-parallel-worktree-writers-conflict|SKY-022 P4 — parallel worktree writers + conflict]]
- **2026-09-04** · session          # session | incident | decision · [[2026-09-04-session-sky-022-p3-checkpoint-continuity-cold-lead-resume|SKY-022 P3 — checkpoint continuity + cold-lead resume]]
- **2026-09-04** · session          # session | incident | decision · [[2026-09-04-session-sky-022-p2-first-real-lead-helper-delegation|SKY-022 P2 — first real lead+helper delegation]]

---
_Human narrative: [[05-state-of-the-lab]] · what to load + its cost: [[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — regenerable from git, never a source of truth._

> [!note] Agent cold-boot digest — generated by `scripts/render-digest.sh` from ADRs + the
> journal + the roadmap. Do not hand-edit. Content-stable (diffs only on real change). The
> human read on the lab is [[05-state-of-the-lab]]; this is the machine orientation layer.
