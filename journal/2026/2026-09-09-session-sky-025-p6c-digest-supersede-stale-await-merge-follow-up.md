---
date: 2026-09-09
time: 21:58:59            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: sky-025 p6c digest supersede stale await-merge follow-up
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "issue #230", "PR #231", "PR #232", "PR #233"]
thread_status: open     # carries the genuinely-current durable follow-ups after P6c fully merged
resolves: [2026-09-09-session-sky-025-p6c-review-fix-regenerate-stale-agent-and-planning-context]
---

# 2026-09-09 · session · sky-025 p6c digest supersede stale await-merge follow-up

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Final P6c review-repair. After PR #231 (implementation) and PR #233 (context refresh; #232 was the
mis-based version) merged to main, the cold-boot digest still carried one stale follow-up from my
earlier review-fix episode:

    P6c + this review-fix await human merge

That is now false — #231/#232/#233 are merged and P6c is complete. The bullet lives in the
append-only episode
`2026-09-09-session-sky-025-p6c-review-fix-regenerate-stale-agent-and-planning-context.md`
(`thread_status: open`), which must not be rewritten.

The digest's follow-up section pulls the 8 newest `open`-episode follow-up bullets, and the journal
has no way for a later session to close an earlier session's threads without editing the old entry.
That gap is why an ephemeral "await merge" bullet stuck around after the PRs merged. Fixed the
current-state derivation, not the history: `scripts/render-digest.sh` now reads a `resolves:`
frontmatter list and skips any episode named there when building the current follow-up view. This
episode `resolves:` the review-fix episode, so its follow-ups (the stale "await merge" plus the
"regenerated surfaces this session" note) drop out while its raw entry stays intact. The genuinely
current durable follow-ups are re-declared below, so the digest reflects them plus the P6 acceptance
episode — no P5/P4 cascade, because six current bullets plus that episode's two fill the 8 window.

## Actions & outcomes
- `scripts/render-digest.sh`: added a `resolves:` pre-pass; the follow-up loop skips superseded
  episodes (raw entries and the Recent-episodes list are untouched). → stale bullet no longer emitted.
- Added `resolves:` to the journal template and documented it in `journal/README.md` (one line each).
- `tests/digest-test.sh`: added a fixture where a newer episode `resolves:` an open episode, asserting
  its follow-up disappears while the other open episode's follow-up remains. → passes.
- Regenerated `docs/generated/06-agent-digest.md` via `render-digest.sh` (never hand-edited). →
  no "await human merge", no #231/#232 pending-merge text; P6c shown complete, SKY-025 6/24.
- Did NOT edit the review-fix episode or any other append-only journal entry.

## Graveyard — tried & abandoned
- Flipping the review-fix episode's `thread_status` to resolved → abandoned: violates append-only
  (no precedent) and, tested earlier, cascades older P5/P4 threads into the digest window.
- Crowding the window with ≥7 padded follow-ups to push the stale bullet past position 8 →
  abandoned as dishonest; there are not that many genuinely-current durable threads.
- A blanket recency cutoff on episodes → abandoned: `tests/digest-test.sh` deliberately asserts more
  than one recent open episode's follow-ups stay visible, so a hard cutoff would regress it.

## Follow-ups / open threads
- **P7a Omada (Terra High) is the sole released executable packet** (directive §5); P7b certs/routes
  and P7c recon are same-phase continuations, and one fresh review covers all P7 before P8.
- **Accepted SKY-025 progress is 6/24**; P7 has not started — never advance a numbered phase without
  its independent acceptance.
- **Offline `config.xml` firewall inventory parsing is retired** (P6c): the live OPNsense API
  (`src/skynet/opnsense.py`) is the sole firewall inventory source, and the `config.xml` git backup
  is DR-only — restored as configuration into OPNsense, never parsed into inventory.
- **Five paused documentation suites** (obsidian-hygiene, documentation-drift, temporal-hygiene,
  repo-surface, hygiene) remain manual during the overhaul; P24 must restore them to hook + CI.
- **Workstation/state/payload recovery and live endpoint parity remain unverified** across the
  overhaul; live transitions still need their existing grant/checkpoint.
- **The OPNsense ops→NET_SKYNET ICMP-vantage floating rule is unverified** (P6 live boundary);
  declared-host presence probing depends on it.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
