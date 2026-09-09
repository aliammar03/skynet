---
date: 2026-09-09
time: 21:41:52            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: sky-025 p6c review-fix regenerate stale agent and planning context
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "issue #230", "PR #231", "ADR 0006"]
thread_status: open     # carries the genuinely-current durable follow-ups after P6 acceptance
---

# 2026-09-09 · session · sky-025 p6c review-fix regenerate stale agent and planning context

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Review-repair packet on top of the P6c implementation (PR #231, branch
`sky-025-p6c-remove-offline-firewall`). The implementation cleanup was judged correct, but P6c was
not accepted because current agent/planning context was still stale: the cold-boot digest still
told agents to build/use `src/skynet/firewall.py` / `collect-firewall.sh` / `skynet collect
firewall`, and the disposition map header still said P5 was current and only P6a released.

Branched `sky-025-p6c-review-fix` off the P6c branch HEAD (`0813661`) — the digest regeneration
depends on the P6c journal entry (its resolved thread) and the map edits already in #231, so this
fix stacks on #231 rather than starting from bare main.

Worked out how the digest resolves threads before touching anything. `scripts/render-digest.sh`
reads each journal entry's *own* `thread_status`; `open` entries contribute their `## Follow-ups`
bullets, newest-first, capped at 8 bullets total; `resolved`/absent are skipped. The stale
firewall.py / "P6b-ii remaining" / #227-#228 bullets came from the P6a/P6b-i/P6b-ii/P6-review
entries, all still `thread_status: open`.

Confirmed the journal is strictly append-only: `git log -S "thread_status: resolved" -- journal/`
shows every `resolved` tag was set on a NEW file at write time; no existing entry has ever been
edited. So editing those P6 entries to `resolved` is not the mechanism. Tested it anyway in a
scratch copy: flipping the four P6 entries to resolved just surfaced even-older P5/P4 "execute
P5 fix / publish P5b" follow-ups — the digest is a rolling recency window, not a per-thread ledger.

The design-consistent fix: this review-fix session is a new `open` entry whose genuinely-current
follow-ups (below) occupy the newest slots and push the stale P6 bullets out of the 8-item window.
Six real follow-ups + the P6-acceptance entry's two bullets fill the window; firewall.py,
"P6b-ii remaining" and the #227/#228 merge-order bullets fall off. No append-only entry was edited.

## Actions & outcomes
- Read `render-digest.sh`, `render-context-map.sh`, `tests/digest-test.sh`, `journal/README.md` to
  learn the maintained mechanism → digest = 8 newest `open` follow-ups, rolling; append-only holds.
- Scratch-tested flipping P6 entries to resolved → surfaced P5/P4 stale threads (cascade) → rejected.
- Wrote this entry `thread_status: open` with 6 current follow-ups → will evict the stale P6 bullets.
- `planning/sky-025-map.md` header rewritten: P6/6-of-24 accepted, P7a released; dropped the P5-current /
  only-P6a-released prose and the obsolete acceptance SHAs (history → §9/git).
- Removed the map's "Phase 6b-ii implementation" section (documented only the removed offline parser);
  neutralized the "P6b … remaining same-phase work" tails in the P6a and P6b-i sections.
- `planning/projects/SKY-020-…md`: fixed the two remaining stale mirror-fallback claims (rollback
  posture line + Phase-1 "no creds ⇒ mirror") → retains prior inventory; parser retired in P6c.
- Regenerated `docs/generated/06-agent-digest.md` and `docs/generated/07-context-map.md` via their
  renderers (never hand-edited). 07 was already clean; 06 now drops the firewall.py instructions.
- Left the directive §9 P6b-i/P6b-ii dated entries and the map's dated slice records as history
  (newest P6c entries record the retirement) — the reviewer allows historical entries to remain.

## Graveyard — tried & abandoned
- Flipping `thread_status: open → resolved` on the P6 journal entries → abandoned: violates the
  append-only invariant (no precedent in git) AND cascades to surface older P5/P4 stale follow-ups.
- Crowding the window with ≥8 padded follow-ups to evict every P6 bullet → abandoned as dishonest;
  used only genuine current follow-ups (6), which is enough to evict the firewall.py/#227-#228 ones.
- Regenerating the inventory-driven docs (00/10/20/…) → abandoned: they are a separate render-docs
  pass driven by inventory JSON that carries unrelated uncommitted local edits; out of scope.

## Follow-ups / open threads
- **P7a Omada (Terra High) is the sole released executable packet** (directive §5); P7b certs/routes
  and P7c recon are same-phase continuations, and one fresh review covers all P7 before P8.
- **P6c + this review-fix await human merge** (PR #231 + the review-fix PR); once merged, the offline
  `config.xml` firewall inventory path is fully retired and the live OPNsense API is the sole source.
- **Five paused documentation suites remain manual** (obsidian-hygiene, documentation-drift,
  temporal-hygiene, repo-surface, hygiene); P24 must restore maintained replacements to hook + CI
  before the directive closes.
- **Generated agent-context surfaces (06-agent-digest, 07-context-map) were regenerated this session**
  to clear stale P6-in-progress/firewall context; they refresh from journal + planning, never hand-edited.
- **Accepted progress is 6/24** (P6 accepted via #229); P7 has not started — never advance a numbered
  phase without its independent acceptance.
- **Workstation/state/payload recovery and live endpoint parity remain unverified** across the
  overhaul; no live/production read or write, root, grant or credential change occurred this session.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
