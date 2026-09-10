---
date: 2026-09-10
time: 21:01:04            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 Phase 3 disposable verification permission follow-up
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-026]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-10 · session · SKY-026 Phase 3 disposable verification permission follow-up

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali accepted Phase 3 and requested one Heavy-route follow-up before Phase 4. The trigger was the first
Heavy deployment's repeated operator permission prompts during disposable T1 mutation probes. The
commands prompting were ad-hoc compound shell probes whose scratch cleanup contained `rm -rf` or an
EXIT trap that ran it. Phase 3 stayed `[x] done`, `current_phase: 3` throughout.

Main used Task ID `sky026-p3-tmp-followup-20260910`. Direct context covered the reported failure,
current construction/sandbox contract, and authority checkpoints. One Companion mapped the local
guidance, role and gate callers; no Investigator was used because no external evidence gap existed.
No Senior Executor was used because the change was bounded guidance plus contract tests.

The first Default Executor wrote the construction convention and runbook paragraphs, then remained
active without returning a report after the focused instruction to conclude. Main interrupted that
worker rather than taking over its package. A replacement Default Executor preserved those edits,
added the same instruction to Default/Senior Executor and Tester role TOMLs, and extended the existing
construction test. The test now uses Python `tempfile`/`shutil` for its fixture directory, checks all
guidance surfaces, and rejects a project-level `approval_policy` override. It did not add a command
allowlist or permission framework.

An independent Tester ran the canonical construction and invariant commands without ad-hoc compound
mutation probes or an operator escalation. It reported 46/46, invariant PASS and clean diff. Main then
reused the Companion with a delta-only conflict check; it confirmed `.codex/config.toml`, AGENTS.md,
root-grant rules, authored-merge rules and Phase 3 state were unchanged.

## Actions & outcomes
- Fast-forwarded local `main` through accepted PR #247 and branched
  `fix/sky-026-p3-tmp-verification-noise` → follow-up starts from accepted Phase 3.
- Added current-state scratch-verification guidance → Main and mutable verification workers use
  canonical tests/encoded fixtures and do not escalate merely for repo-local or TMP-only cleanup.
- Replaced `mktemp -d` plus EXIT `rm -rf` in `tests/construction-test.sh` with Python
  `tempfile.mkdtemp` plus `shutil.rmtree` → the canonical mutation fixture path has language-native
  lifecycle cleanup.
- Added guidance-removal and project-approval drift fixtures → `bash tests/construction-test.sh`
  reported 46 passed, 0 failed; `./scripts/check-invariants.sh` and `git diff --check` passed.
- Preserved workspace-write, inherited on-request approval, root-grant and authored-merge checkpoints
  → no T2/T3, production, secret, grant, merge, broad `rm`, or allowlist change occurred.
- Preserved the pre-existing untracked `inventory/tofu-drift.txt`.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Waiting for the first Executor after one focused conclusion instruction → abandoned when the
  bounded worker remained active without a report; Main interrupted it and reassigned the same
  ownership rather than implementing the package.
- Broad `rm` allow rules, `approval_policy = "never"`, and a separate permission framework → not
  attempted because the failure was command shape and repeatability, not missing authority.

## Follow-ups / open threads
- Phase 4 remains the next directive phase after this bounded follow-up is human-merged.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
