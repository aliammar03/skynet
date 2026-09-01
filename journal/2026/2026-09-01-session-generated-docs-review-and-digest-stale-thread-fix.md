---
date: 2026-09-01
kind: session          # session | incident | decision
title: generated-docs review and digest stale-thread fix
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-018, "PR #135"]
---

# 2026-09-01 · session · generated-docs review and digest stale-thread fix

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Read through every `docs/generated/` page after the unattended nightly (PR #134, merged) to check
for mistakes. Found a **feedback loop that writes false facts to the record every night**:

- `06-agent-digest.md` pulls the newest 8 "open-thread" bullets from journal entries **verbatim**.
  The journal is append-only, so threads raised in the P1 entry
  (`2026-09-01-session-sky-018-p1-first-entity-audit`) — written **before** the destroys — still sit
  there as "open". `render-digest.sh` had no way to know they were resolved.
- The nightly engine (codex) then **copied them forward**: tonight's journal entry
  (`…-nightly-2026-09-01-1735-rerun.md`, merged to main via #134) re-listed them in its own
  Follow-ups, and `05-state-of-the-lab.md` printed them under "Human attention" as live issues.

The false claims, all about guests Ali **destroyed earlier today** (verified 0 occurrences in
`inventory/proxmox-*.json`):
- "CT 526 remains running and unmapped" — 526 (UniFi controller) destroyed.
- "Resolve ownership of 10.10.100.35 before any destruction of stopped CT 1035" — CT 1035 destroyed;
  `.100.35` is the `caddy-apps` container (DMZ macvlan), not a guest.
- "Confirm VMIDs 101, 231, 999, 9091 were intentionally removed" — all destroyed, settled in the
  P1 triage decision (`2026-09-01-decision-arcane-relocation-and-sky-018-audit-triage`).

The one genuinely-new thread codex raised was correct and kept: `vm-skynet-ops` (9090) uptime reset
~3.9d → ~3.9h. Cause is now known — Ali's `nixos-rebuild switch` after merging the P4 collector PR
(#133) to materialize `/opt/skynet-ops/secrets/omada.env`. Not a crash.

Also surfaced (faithfully rendered, but the OPNsense **source** data is stale — T3, Ali's to clean):
- `HOST_SKYNET_OPS` alias = `10.10.90.90, 10.10.90.91`; `.91` is a leftover from the pre-SKY-007
  9091 ops VM (renumbered to 9090). Shows in 00-network-map + 20-firewall.
- `ap-omada-downstairs` DHCP reservation still at `.7` (the optional cleanup we skipped); the AP is
  static in Omada now and renamed "Mom's AP", so the VLAN map shows a stale name.

## Actions & outcomes
- `render-digest.sh` → added `thread_resolved()`: drop an open-thread bullet that names guests
  (`CT|VM|VMID <n>`) when EVERY named guest is absent from inventory. Keyword-anchored on purpose —
  broadening to bare numbers wrongly ate `SKY-019`/`SKY-018` refs. Regenerated `06-agent-digest.md`:
  the CT 526 / CT 1035 / 101-231-999-9091 bullets are gone; 9090 + PBS threads stay.
- `tests/digest-test.sh` (NEW) → renders the digest against a fixture journal + real inventory,
  asserts destroyed-guest threads drop and live/guest-free threads survive. Wired into CI +
  `.githooks/pre-commit` (gate 5). 5/5.
- Corrected `05-state-of-the-lab.md` by hand (it is agent-authored, not a deterministic render, and
  I am the agent): dropped the destroyed-guest items, named the 9090-restart cause, added the P4
  landing under "what changed".
- One residual: the P1 entry's `**P2 next:** … arcane-manager, 101, 526, 999 …` bullet uses **bare**
  numbers (no CT/VM prefix) so the filter leaves it; it is stale (P2/P3/P4 done, arcane → SKY-019)
  and will age out. Recorded here so it is not mistaken for live.

## Graveyard — tried & abandoned
- Broadening the filter to suppress bullets by ANY absent 2–5-digit number → abandoned: `SKY-019`
  and `SKY-018` parse as `019`/`018`, which aren't VMIDs, so legit planning threads got dropped.
  Kept the match keyword-anchored (`CT|VM|VMID <n>`).

## Follow-ups / open threads
- OPNsense (T3, Ali): trim `HOST_SKYNET_OPS` to `10.10.90.90` (drop the stale `.91`); optionally
  remove the `ap-omada-downstairs` reservation now the AP is static.
- PBS snapshot verification + the L5 Google Drive mirror remain unproven without the PBS credential /
  a root grant (carried, genuinely open).
- SKY-018 P5 (Caddy route + cert collectors) is next for the entity spine.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
