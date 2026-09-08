---
date: 2026-09-08
time: 17:34:21            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P3 combined re-review
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR 215", "PR 216", "PR 218"]
thread_status: open
---

# 2026-09-08 · session · SKY-025 P3 combined re-review

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali asked to review the fix together with #215/#216 and release the drafted next packet only
after full P3/G2 acceptance. GitHub confirmed #215 at
`05b6326c46506b1c936fbaae724a083d8a218954`, #216 at
`8e6c8502ba7c9ce8e9d39fe9bd6d5fd5a45a36df`, and #218 at
`1a08ebc6845f7e75ef29f2a4c3930ca07b9b1d2a`, all merged. Main was the #218 SHA,
including on the pre-publication recheck. The comparison starts at accepted P2
`17db700c22cb17ad219655674eada344c215029a`; #214/#217 contribute planning changes.
The live checkout had generated inventory/docs changes. I created
`/tmp/skynet-sky-025-p3-rereview` at reviewed main and did not alter the live checkout.
The branch became `fix/sky-025-p3-credentials` when Ali authorized implementing simple fixes.

Installed catalog lists Astra Medium and `bin/agent review --dry-run` selected it. A bounded
Luna scout inspected reader cleanup; it found no ordinary-group cleanup defect and identified
the limit for children escaping via setsid/setpgid. Its direct pytest invocation was unavailable;
my Nix-owned suite ran the actual timeout/SIGINT/SIGTERM/early-exit cases successfully. The
existing reader scripts contain no setsid/setpgid/daemonization calls. I documented that runner
limit rather than claiming arbitrary process-tree containment.

The merged parser accepted exactly three assignments, but `collect-proxmox-acl.sh:10-23`,
`tofu-env.sh:54` and `pve-snapshot.sh:45-47` consume `PVE_TOKEN_OPERATE` from the same file.
A disposable synthetic four-assignment probe returned exit 3, zero requests, retained bytes,
and `invalid credential assignments; refresh failed; any retained snapshot is previous evidence`.
No real credential file was read. This contradicted the integrated default-path contract.

Ali directed me to implement simple fixes myself, then to open P4 if fixed, and explicitly
rejected another review round. I repaired the optional assignment handling in this branch,
tested it, and included P3/G2 acceptance plus P4a release effective at human merge. This is
an explicitly authorized exception to the additional merged-fix review, not self-merge authority.

## Actions & outcomes
- Original main: `nix develop --no-write-lock-file -c pytest -q` → 94 passed in 17.29s.
- Added the optional known assignment to the parser allowlist; required read credentials remain
  required. No fallback to operate, shell evaluation, token logging or transport change.
- Shared credential fixture now contains distinct read and operate strings, so original CLI,
  HTTPS-header and default-caller tests exercise the shared format. Five added cases cover
  optionality/no fallback and duplicate/expression/empty/unknown assignment refusal.
- Fixed branch: complete pytest → 99 passed; Ruff clean; mypy clean in six source files.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → exit 0,
  including source and installed behavioral coverage. Offline launcher doctor returns runtime
  success; missing-evidence status returns unavailable. No profile installed.
- Full-phase source inspection covered CLI, validation, TLS/redaction, snapshot publication,
  durable receipt/status, default shell callers, renderer cache handling, nightly same-pass
  cutoff, package filter and CI/hook changes. R1/R2 regressions remain passing.
- P4a keeps Terra High, adds network observation/default freshness; P4b owns both operate-token
  ACL observations and their freshness. The P4 draft's credential repair moved into P3, so
  P4 now explicitly reuses the fixed parser. No new framework or roadmap reorder.
- No lab API, real credential, T2/T3, root, activation, timer, host or payload/state operation.

## Graveyard — tried & abandoned

Final verification before publication: `nix flake check --no-write-lock-file --no-build`
returned 0 (existing system/meta/deploy warnings only). The full staged `.githooks/pre-commit`
returned 0, including secret scan, privilege/pool invariants, entity/SQLite, rollback/provisioning,
construction/routing and nightly merge/sequence tests; its Python run passed all 99 cases in
17.10s, followed by clean Ruff/mypy. `git diff --cached --check` returned 0. The five paused
documentation suites were not run or counted as passing.

Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Initial disposable probe imported the pytest fixture module; the development Python did not
  expose that module/pytest through the attempted PYTHONPATH overrides. Replaced that dependency
  with a minimal request sentinel and reproduced the parser failure with stdlib only.
- Do not defer shared credential compatibility to P4: core's existing default file already
  uses that contract. Do not require another review round after Ali explicitly removed it.

## Follow-ups / open threads
- After Ali merges this credential-fix/P4 packet PR, execute SKY-025 §5 Phase 4a with Terra High via planning/prompts/execute.md. No additional P3 review round is required; accepted progress is 3/24.
- Independent workstation/state/payload recovery and live API/TLS parity remain unverified before a live transition. The five paused documentation suites remain unrun and must return as maintained checks by P24.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
