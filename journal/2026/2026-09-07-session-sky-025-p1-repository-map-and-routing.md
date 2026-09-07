---
date: 2026-09-07
time: 12:54:44            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P1 repository map and routing
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR 208, PR 209, PR 210]
thread_status: open
---

# 2026-09-07 · session · SKY-025 P1 repository map and routing

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali asked to start SKY-025. Read the cold-boot digest/context map, planning lifecycle, directive and
execute handoff, constitution and relevant conventions. The digest still listed SKY-023 as 4/6;
the current directive was 10/10 in progress. Used source directives for ownership decisions.

`git fetch origin main` resolved `670f06cfa75ca95a9eac7fdb1d3eb3544272ff1a`. `gh pr list --state open`
showed no SKY-025 implementation PR; #203 was an open SKY-023 review branch, plus Renovate PRs.
Main already contained bootstrap planning #208 and handoff #209. The original checkout held
unrelated modified inventory/generated files and untracked `inventory/tofu-drift.txt`.
Created `/tmp/skynet-sky-025-p1` with `git worktree add -b phase/sky-025-p1 ... origin/main`.

Read only model/effort/cwd fields from current session turn metadata: `gpt-6-astra`, `medium`,
`/home/aliammar/skynet`. `codex --version` returned `codex-cli 0.153.4`. Selected slug and supported
effort fields from the installed model catalog: Astra medium, Terra high, Sol low and Luna
medium/high all present. Consulted the official Codex configuration reference via OpenAI Docs.
Launched two native Luna Medium scouts with read-only, file-bounded inventory and routing/overlap
packets; no writer workers or production credentials were used.

`systemctl show skynet-nightly.service skynet-cli-update.service -p Id -p FragmentPath
-p WorkingDirectory -p ActiveState` showed both services inactive, installed under
`/etc/systemd/system/`, using `/home/aliammar/skynet`. `systemctl list-timers --all --no-pager
skynet-nightly.timer skynet-cli-update.timer` showed both scheduled. Inspected local cert/mirror/cache
directory metadata and ignored-file names only. No secret/state/backup contents were read or copied,
no remote host was contacted for inspection, and no services/timers were changed.

## Actions & outcomes
- `git ls-tree -r --name-only origin/main | wc -l` → 398 tracked paths. Checked grouped family counts;
  50 scripts-directory paths and 6 bin entries. The map includes service PHP/JS/config, CA/public keys,
  encrypted files, root config, Obsidian, Nix activation/timers and workstation/host-local callers.
- Changed `bin/agent`: explicit `lead --tier astra|terra|sol`, default Terra High, fresh `review`
  Astra Medium, Builder/Mechanic Luna High and Scout Luna Medium. Removed `--hard`; updated its known
  runbook callers and tests. Kept all sandboxes, two-worker cap and worktree-root validation.
- Native builder now selects Luna High. Added explicit worker no-commit/push/merge and no-helper
  instructions where missing. `.claude/settings.json` and `CLAUDE.md` inspected and retained: shared
  operator permission/import surfaces, no conflicting model router; operator push permission does
  not authorize worker pushes.
- Replaced benchmark routing prose with the approved phase routing and independent review contract.
  Changed capability conventions to Python for new procedural code, explicit outcomes, safe external
  boundaries and Nix ownership. Existing shell implementations remain described as installed.
  Removed the old token-budget narration from the documentation convention. No invariant, saved-plan
  executor, auto-merge gate, production package or schedule changed.
- Added disposition/ownership notes to SKY-005/006/012/015/016/017/018/020/023/024. Preserved their
  progress and unrelated features/migrations. Ran `bin/plan start SKY-025`: one project copy,
  in-progress, updated 2026-09-07, accepted phase count still 0. Phase 2 not implemented or fleshed out.
- `bash tests/agent-test.sh` → 82 passed, 0 failed; native/standalone parity, all lead/review routes,
  invalid combinations, explicit override and worktree rejection cases. These are dry-runs, not live
  Terra/Sol/Luna High calls. Luna Medium workers and this Astra Medium session actually ran.
- `bash tests/construction-test.sh` → 8 passed, 0 failed; `scripts/check-invariants.sh` passed.
- `.githooks/pre-commit` → exit 0: secret scan, invariant gate and all 19 shell suites passed.
  Entity suite: 47 checks, including SQLite joins (sqlite3 available, no SQLite skip).
  Other suite counts: digest 10, DNS revert 14, Compose rollback 11, certificate selector 4,
  Tofu rollback 22, PVE snapshot 2, provisioning truth 12, PBS collection 14, construction 8,
  agent 82, gitignore 3, Obsidian 4, nightly automerge 10, nightly sequence 10,
  documentation drift 8, temporal hygiene 6, repo surface 12, hygiene 5; all zero failures.
- `bash -n bin/agent tests/agent-test.sh`, Claude settings JSON shape, `git diff --cached --check`,
  and unique `bin/plan show SKY-025`/frontmatter checks passed. No Nix/Tofu production evaluation,
  install, apply, backup or recovery drill was performed; P1 changes no Nix/Tofu declarations.

## Graveyard — tried & abandoned
- Initial scout surface report described the original checkout's dirty state despite the assigned
  worktree and reported an incorrect total of 441 files. Requested a workdir-explicit rerun, then
  independently counted main at 398. Used corrected paths/counts in the map; no scout edited files.
- Routing scout proposed renaming launcher roles to phase/worker; kept existing roles and added
  explicit tier/review options to avoid an unnecessary interface overhaul. Its unavailable-model
  note guessed `gpt-5.6-astra`; used the installed `gpt-6-astra` catalog/session evidence instead.
- An apply_patch request combining delete/add for the same construction-doc path was rejected
  atomically. Replaced the existing file with an update patch; no intermediate file deletion.
- ShellCheck is not installed; Bash syntax plus behavioral routing tests were used. No package
  installation or production model probes were added to this T1 phase.

## Follow-ups / open threads
- Human merge of the Phase 1 implementation PR, then fresh Astra Medium G1 review. Keep accepted
  progress at 0 until that reviewer accepts; only its human-merged next packet releases Phase 2.
- Map explicitly blocks affected live phases on Arcane commands/revisions, remote host-local
  backup installs/units/OS, and independent workstation/kit/state/payload recovery checks. Unknown
  remote state is not evidence that callers are absent. Nothing is stopped to restore in P1.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
