---
date: 2026-09-10
time: 21:43:13            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 Phase 4 continuity and token accounting
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-026, viettran-edgeAI/codex_workflow@6d9b06f73bee7f899001b0bb102c70529a24313f]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-10 · session · SKY-026 Phase 4 continuity and token accounting

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali requested SKY-026 Phase 4 only. The deployment used Task ID `sky026-p4-20260910` and accounting
ID `sky026_p4_20260910`. Main read the directive and decision-critical construction/planning
contracts; one native Companion read the bulky continuity surface and returned the current closure,
planning-template and token-evidence gaps. No Senior Executor was used because this Medium phase kept
implementation and verification with Main. No production host, credential, grant, or T2/T3 action was
touched.

Cloned `viettran-edgeAI/codex_workflow` into `/tmp/sky026-p4-donor`; current upstream and the directive's
pinned donor both resolved to `6d9b06f73bee7f899001b0bb102c70529a24313f`. Read the donor Archivist,
Medium/Heavy closure marker, deployment-token-report skill, parser and behavioral tests. Local Codex
0.153.4 stored rollout JSONL under `/home/aliammar/.codex/sessions/` and indexed parent/role metadata in
`state_5.sqlite`. A diagnostic run over the active Main+Companion ancestry returned recorded input,
cached-input and output counts with no warnings; no price was calculated.

## Actions & outcomes
- Reworked current construction continuity → Main reads the Direct set once; Companion owns bulky
  intake and later delta/conflict checks; active directives and raw journal evidence remain canonical.
- Defined complete/paused/blocked closure → each state has exactly one directive-owned next-session
  entry point; `.agent/CHECKPOINT.md` remains optional disposable state.
- Ported the donor reporter into `.agents/skills/deployment-token-report/` → retained ancestry,
  boundary, fail-closed parsing and six-column output; renamed only the deployment marker for Skynet.
- Updated Archivist → it seals closure after assigned docs/checks, never decides acceptance or edits
  generated truth, and returns only the exact recorded report or exact limitation.
- Ran `codex debug prompt-input` from the repo → the installed harness listed
  `deployment-token-report` from `/home/aliammar/skynet/.agents/skills`.
- Ran `python3 -B -m unittest -v tests/test_deployment_token_report.py` → 11 tests passed, including
  complete/paused/blocked continuation, missing/ambiguous markers, ancestry, guardian exclusion,
  late-marker rejection, incomplete-tail evidence behavior, and Archivist-only closure ownership.
- Ran `bash tests/construction-test.sh` → 46 passed, 0 failed.
- Migrated current planning templates/directives away from nonexistent `SKY-###-progress`/`MEMORY.md`
  handoffs and stale Scout wording; archive/journal history was not rewritten.
- Ran `bin/plan list` → SKY-026 rendered `4/5`, status `in-progress`.
- The Companion's delta/conflict check found one live optional `SKY-025-progress` caller → removed it;
  it also confirmed this deployment's first commentary predated the newly introduced hidden-marker
  contract. The closing Archivist must return that exact limitation instead of treating the later
  marker or Main's diagnostic report as closure evidence.
- Tightened `find_boundary` after that check → the parser now verifies record order and fails unless
  the marker is in the first Main assistant message after the deployment's user turn.

## Graveyard — tried & abandoned
- `.codex/skills/deployment-token-report/` → abandoned before commit because installed Codex does not
  discover repo-local skills there. Official/local discovery evidence identified `.agents/skills/`;
  the untracked prototype files were removed and the skill was added at the discovered path.
- `python3 -m py_compile` against the read-only `.agents`/`.codex` control surface → abandoned because
  it tried to create `__pycache__`; `python3 -B <script> --help` and the behavioral suite validate the
  source without cache writes.
- First closure-contract assertion matched the wrong newline shape → corrected the assertion; all
  production parser cases had already passed in that run.

## Follow-ups / open threads
- Ali must merge the authored Phase 4 PR. Then execute SKY-026 Phase 5; no Phase 5 work occurred here.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
