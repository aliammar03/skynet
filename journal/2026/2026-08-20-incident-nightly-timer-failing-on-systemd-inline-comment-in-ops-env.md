---
date: 2026-08-20
kind: incident          # session | incident | decision
title: nightly timer failing on systemd inline-comment in ops.env
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-005, "PR #87"]   # surfaced by recon.sh (SKY-005 P1); fix PR opened same day
---

# 2026-08-20 · incident · nightly timer failing on systemd inline-comment in ops.env

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
While reviewing the SKY-005 P1 recon toolkit, `scripts/recon.sh local` on vm-skynet-ops flagged
`skynet-nightly.service` in a `failed` state — first real signal recon produced. Investigated
imperatively (T1, no grant).

`systemctl status skynet-nightly.service`:
```
Active: failed (Result: exit-code) since Thu 2026-08-20 03:32:00 UTC
Process: 148747 ExecStart=/home/ali/skynet/bin/ops nightly (code=exited, status=2)
ops[148747]: unknown OPS_ENGINE 'codex                 # codex | claude' (use codex|claude)
```

Root cause: `/home/ali/.config/skynet-ops/ops.env` (and its repo source
`scripts/systemd/ops.env.example`) had `OPS_ENGINE=codex                 # codex | claude`.
The unit loads it via `EnvironmentFile=-`. **systemd's EnvironmentFile does NOT strip inline
`# comments`** — everything after `=` is the literal value — so `OPS_ENGINE` became the string
`codex                 # codex | claude` (trailing whitespace + comment). `bin/ops`'s
`engine_bin` correctly rejected it → exit 2 → nightly never ran. Failing every night since the
env file took this form (recon showed a prior failure Aug 16 too).

Sneaky because `bin/ops` is *also* run manually via bash, and **bash sourcing DOES strip the
inline `# comment`** — so it only broke on the systemd path (the timer), never when tested by hand.

## Actions & outcomes
- Fixed live `~/.config/skynet-ops/ops.env`: moved the `codex | claude` hint to its own comment
  line; `OPS_ENGINE=codex` now bare. Same for the (commented) FALLBACK / NIGHTLY_MODE / ENGINE_CMD
  lines so uncommenting them later is safe. → done
- Verified with systemd's own parser (not bash):
  `systemd-run --user --wait -p EnvironmentFile=… env bash -c 'echo $OPS_ENGINE'` → `[codex]`. → clean
- Verified `bin/ops`' engine gate now passes: same env + `bin/ops __probe__` → `unknown command:
  __probe__` (reaches command parsing; old bug died earlier at `unknown OPS_ENGINE`). → passed
- Fixed the repo source `scripts/systemd/ops.env.example` the same way + a load-bearing note that
  systemd keeps inline `#` in the value → PR (declarative fix so no one re-copies the bug).

## Graveyard — tried & abandoned
- `systemctl reset-failed skynet-nightly.service` → refused ("Interactive authentication
  required"); it's a system unit and I hold no standing root. Not worth a grant for a cosmetic
  state clear — the next timer run (Fri 2026-08-21 03:31 UTC) flips it green end-to-end.

## Follow-ups / open threads
- Confirm the Fri 2026-08-21 03:31 UTC timer run goes green (proves the fix end-to-end + clears
  the failed state on its own).
- Class of bug worth a guard: any `EnvironmentFile` we ship must keep comments on their own line.
  Candidate for a tiny lint (grep for `^[A-Z_]+=.*#` in `scripts/systemd/*.env*`) if it recurs.
