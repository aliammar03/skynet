---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-022 P2 — first real lead+helper delegation
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-022, "PR (phase/sky-022-p2)", bin/agent, scripts/check-invariants.sh, invariants.json]
---

# 2026-09-04 · session · SKY-022 P2 — first real lead+helper delegation

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Executed SKY-022 Phase 2 (prove lead-driven delegation on a real T1/repo task). This session is
**Claude Code (Opus 4.8)**, not a Codex Terra/Sol lead as the directive's default assumes. I acted
as the accountable lead and delegated one level to **real Codex helpers via `bin/agent`** — the
"standalone mirror" path the doctrine defines for exactly a non-Codex lead. Cross-vendor by
AGENTS.md contract; recording it as P2 evidence.

Task chosen: make the construction doctrine's own `[testable]` claims actually machine-enforced.
`docs/conventions/construction.md` tagged the ≤2-helper cap and scout-read-only `[testable]` ("a
lint/config gate could assert it") but `scripts/check-invariants.sh` enforced neither — the P1
doctrine was prose, not a checker. Two natural subtasks: a read-only investigation and a bounded
implementation.

`codex` is live here: `codex-cli 0.149.0`, `codex login status` = "Logged in using ChatGPT".

Trajectory:
1. Branched `phase/sky-022-p2`.
2. Launched the read-only **Scout** — `bin/agent scout "<prompt>"` → **died instantly**:
   `error: unexpected argument '--ask-for-approval' found`. Root cause: P1's `bin/agent` passed
   `--ask-for-approval` to `codex exec`, but in v0.149.0 that flag lives on the top-level `codex`
   command, NOT the `exec` subcommand. P1 wrote the launcher from researched CLI facts that don't
   match the installed build.
3. Lead fixed `bin/agent` (judgement/debug task — not BIV-delegatable): dropped the flag +
   `approval` variable. `codex exec` is already non-interactive, so `--sandbox` IS the leash and
   there's nothing to approve; escalation beyond the sandbox is denied, not prompted — the exact
   build-time posture we want. Added a comment warning off `--dangerously-bypass-*` / `--approve-for-me`.
   Committed alone (c01accc) so the tree was clean before the writer ran.
4. Re-ran Scout (gpt-5.6-luna, medium, read-only). Banner confirmed the model IDs are REAL, not
   placeholders: `model: gpt-5.6-luna / approval: never / sandbox: read-only`. It returned a sourced
   report: all 4 `[testable]` claims with line numbers, the enforcement gap, exact config literals,
   and integration facts (jq pattern, CI + hook wiring, house test style). I re-checked every
   file:line against the tree — accurate.
5. Launched **Builder** (gpt-5.6-terra, high, workspace-write) with a BIV prompt (scope surface =
   3 named files, expected output, NO commit, exact verification commands). It edited exactly those
   3 files, ran the verifications, and reported green.
6. Lead verified independently (never trust helper "done"): read the full diff; ran the gate (6/6),
   the new test (8/8), JSON validity, and — the real proof — mutated the live `.codex/config.toml`
   cap 2→3 and scout `read-only`→`workspace-write` and confirmed the gate FAILS each with an
   actionable message, then `git checkout`-restored. No regression across the other 6 suites.
7. Integration the helper couldn't own: wired `construction-test.sh` into `.githooks/pre-commit` +
   `.github/workflows/checks.yml` (else orphan test), and updated `construction.md` so the
   `[testable]` tags point at their checker. Committed as the lead (6dd7f2e).

## Actions & outcomes
- `bin/agent scout ...` (1st) → FAIL, `--ask-for-approval` rejected by codex exec 0.149.0.
- Fix `bin/agent`, commit c01accc → dry-run + live scout both clean.
- Scout (luna) → accurate sourced gap report; every file:line verified by the lead.
- Builder (terra) → invariants.json `construction` section + check #6 + tests/construction-test.sh;
  touched only the 3 in-scope files.
- Lead gate run → 6/6 checks OK, construction-test 8/8, negative proofs both fail-closed as intended.
- Wired test into hook + CI; construction.md `[testable]`→checker note; commit 6dd7f2e.

## Graveyard — tried & abandoned
- **`--ask-for-approval` on `codex exec`** → abandoned; not a valid `exec` flag in v0.149.0. Correct
  mapping: none — the sandbox is the whole leash for a non-interactive run. (`--approve-for-me` and
  `--dangerously-bypass-*` exist but are deliberately NOT used — construction never earns access
  wider than its role's sandbox.)
- **Watcher grepping the codex trace for `error:` to early-bail** → abandoned; false-matched the
  helper's own narration and killed the wait loop. Only process-exit is a reliable "done" signal.
- **`pkill -f "codex exec…"` to clean stale waiters** → abandoned; the pattern also matched my live
  `run_in_background` watcher shells (their command string contains "codex exec"), turning clean
  completions into exit-144 "failed" notifications. Kill by PID, not by a pattern that matches the
  watcher too.

## Follow-ups / open threads
- `codex exec` writes its transcript (banner + reasoning + exec trace) to **stderr**; only the final
  agent message goes to **stdout**. `bin/agent` inherits both — fine for a terminal lead, but a
  programmatic caller (P6 App Server) will want structured capture, not stdout/stderr scraping.
- Local pre-commit hook is NOT active in this env (`git config core.hooksPath` unset). Ran every gate
  manually; CI (checks.yml) is the backstop. Worth confirming `bootstrap-workstation.sh` sets
  hooksPath on the machines that matter.
- One-level delegation depth stays `[manual]` — Codex exposes no "a helper cannot spawn a helper"
  config knob to assert. If a future version does, promote it to check-invariants.sh.
- Cross-vendor wrinkle: doctrine's default lead is Terra/Sol; this ran with a Claude lead + Codex
  helpers and worked cleanly. The role→tier table is about *helpers*; the lead's engine is
  incidental. Consider a one-line note in construction.md if this recurs (deferred — not yet a pattern).
- Delegation verdict for P5: the Scout paid off (it produced a tight, verifiable spec and kept the
  lead's context off file-spelunking); the Builder paid off (bounded logic + test to a clear
  interface). The launcher bug was NOT delegable and correctly stayed with the lead. No coordination
  tax beyond the codex-CLI drift, which was a one-time P1 fact-rot, not a delegation cost.
