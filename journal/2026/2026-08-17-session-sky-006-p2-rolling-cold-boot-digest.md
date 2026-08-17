---
date: 2026-08-17
kind: session
title: SKY-006 P2 — rolling cold-boot digest
tier_touched: [T1]
grants: []
refs: [SKY-006, "phase/sky-006-p2-digest", scripts/render-digest.sh, docs/generated/05-state-of-the-lab.md]
---

# 2026-08-17 · session · SKY-006 P2 — rolling cold-boot digest

## What happened
Executed SKY-006 Phase 2 the same day as P1. Goal: a cold-boot digest (state + recent decisions +
open threads) that read-time-assembles from ADRs + the journal + the roadmap, without re-summarizing
raw episodes, so a fresh session orients from one page.

First cut embedded the digest as a marker-delimited block spliced INTO `05-state-of-the-lab.md`.
Opened PR #48, then Ali redirected mid-flight: keep 05 a **human** narrative (and surface it in the
top-level README), and make the digest its **own agent-facing page**. Re-architected accordingly.

Final shape: `scripts/render-digest.sh` (deterministic, read-only, idempotent, content-stable — no
per-run timestamp) generates a standalone `docs/generated/06-agent-digest.md` with three sections —
Recent decisions (ADRs newest-first, parsing `**Status:**`/`**Date:**` + the H1), Open threads (open
`SKY-###` via frontmatter `status`, ordered projects→backlog→ideas, then the journal's own
`## Follow-ups` bullets harvested verbatim with continuation-line joining), Recent episodes (last 7
journal entries as wikilinks). 05 restored to a clean human narrative that footer-links the digest.
Wired render-digest into both nightly paths (deterministic path now regenerates 06 even LLM-free).
Pointers: `AGENTS.md` (cold boot → read 06), `docs/design/observability.md` (05 human / 06 agent
split), `README.md` (features 05 + links 06), render-docs index (lists 06).

## Actions & outcomes
- `scripts/render-digest.sh` → generates `06-agent-digest.md` cleanly; `bash -n` clean; `chmod +x`.
- Verified **idempotent**: two consecutive runs produce a byte-identical page (diff -q clean).
- Open-threads harvest joins soft-wrapped journal bullets (awk accumulates until next bullet / blank
  / heading) so nothing renders truncated mid-sentence.

## Graveyard — tried & abandoned
- **Embedding the digest as a marker block inside `05-state-of-the-lab.md`** — abandoned after
  Ali's feedback (was PR #48's first cut). Two problems it caused: 05 stopped being a clean human
  page, and the agent nightly (which rewrites 05 prose) had to be trusted to preserve the markers.
  Split into a standalone `06-agent-digest.md`: 05 stays human (and README-featured), 06 is the
  machine page — no marker-preservation dance, no splicing awk, simpler renderer.
- **Timestamp inside the digest** — abandoned. It made the page diff every single nightly even when
  nothing changed (pure noise → a PR every night). Content-stable now; diffs only on real change.
- **awk that grabbed only the first line of each `## Follow-ups` bullet** — abandoned. Journal
  bullets soft-wrap, so open threads rendered truncated mid-sentence. Replaced with continuation-joining.

## Follow-ups / open threads
- Phase 3: git-rebuildable local semantic index (sqlite-vec class) — still deferred until
  markdown + grep visibly strains (research "overkill line").
- Open-threads harvest scans the most recent journal entries until it has 8 bullets; a thread can
  appear twice if two entries mention it. If the journal grows noisy this may want an "resolved"
  prune convention or a dedup pass.
