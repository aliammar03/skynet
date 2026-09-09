---
date: 2026-09-09
time: 21:10:28            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: sky-025 p6c remove offline firewall inventory path
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "issue #230", "PR #229", "ADR 0006", "SKY-020"]
thread_status: resolved # resolves the P6b-ii "offline parser" thread by removing that path
---

# 2026-09-09 · session · sky-025 p6c remove offline firewall inventory path

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Authorized by GitHub issue #230 (SKY-025 P6c) — a bounded corrective slice after P6 ACCEPT (#229,
commit `4bc4715`). Goal: remove the offline OPNsense `config.xml` firewall-inventory parser entirely
so the live OPNsense API (`src/skynet/opnsense.py`) is the sole firewall inventory producer. P6b-ii
had shipped `src/skynet/firewall.py` + `scripts/collect-firewall.sh` + `skynet collect firewall`,
which rebuilt `firewall.json` from the git mirror — a second producer for the same inventory shape,
deliberately never live-fresh, and a source of live-vs-stale provenance ambiguity.

Branched `sky-025-p6c-remove-offline-firewall` from remote main `4bc4715` (working tree carried
unrelated uncommitted inventory/docs edits + `inventory/tofu-drift.txt`, all preserved and left
unstaged).

Mapped every reference with grep across `*.py *.sh *.nix *.md *.toml *.yml`. Split the
`tests/fixtures/firewall/` dir: `config.xml` was the offline-parser-only fixture (deleted); the
`tests/fixtures/opnsense/*.json` files belong to the live collector (kept). DR references
(`disaster-recovery.md`, `runbooks/dr/*`, gitops-loop/architecture backup-repo mentions) describe
restoring `config.xml` as configuration into OPNsense — preserved as DR material, not touched.

## Actions & outcomes
- `git rm src/skynet/firewall.py tests/test_firewall.py scripts/collect-firewall.sh tests/fixtures/firewall/config.xml` → removed (firewall dir now gone)
- `src/skynet/cli.py` → dropped the `firewall` import, subparser, and dispatch branch
- `tests/test_collection.py` → removed `firewall` from the package import; rewrote
  `test_offline_mirror_replacement_invalidates_existing_live_receipt` →
  `test_out_of_band_firewall_overwrite_invalidates_existing_live_receipt`, which appends a byte to
  `firewall.json` directly instead of calling the deleted parser. Preserves the receipt sha256
  mismatch → status 3 coverage (verified against `collection.py:399`).
- `nix/packages/skynet.nix` → removed `test_firewall.py`, `fixtures/firewall`, `collect-firewall.sh` from the source filter
- `nix/modules/base.nix` → reworded the `python3` comment (was "collect-firewall.sh parses…"); python3 still needed by the whole engine
- `.githooks/pre-commit` → removed `tests/fixtures/firewall/*` and `scripts/collect-firewall.sh` from the python-changed glob
- `scripts/render-docs.sh` → 20-firewall warning now points only to `collect-opnsense.sh` (live)
- `scripts/collect-opnsense.sh` → header comment now states it is the sole firewall inventory source; config.xml backup is DR-only
- `nix/README.md` → deleted the `skynet collect firewall` paragraph; reworded the opnsense-paragraph tail (live API sole source, config.xml = DR-only)
- `docs/design/observability.md` → reworded the "offline config.xml mirror parser is the DR rebuild source" sentence
- `docs/decisions/0006-…md` → Context reference genericized (no script name); Consequence amended in place to record the offline parser retired in P6c, config.xml git backup DR-only (restored as config, never parsed to inventory)
- `planning/projects/SKY-020-…md` → updated the two `collect-firewall.sh` references (scope + Phase 1) to the live collector / DR backup
- `planning/sky-025-map.md` → updated the disposition row; added a "Superseded by P6c" banner to the 6b-ii record; added a "## Phase 6c disposition" section
- `planning/projects/SKY-025-…md` → added a P6c §9 status entry (accepted progress stays 6/24; corrective slice)

Checks (nix dev shell, `--no-write-lock-file`):
- `pytest -q tests` → 218 passed (test_firewall.py's ~6 parser tests gone; no failures). Full `pytest -q` hits a pre-existing `INTERNALERROR` because the repo's `result` symlink (a prior `nix build` of the host system) drags idlelib tests into collection — unrelated to this change; scoping to `tests/` is what the directive's own P6 check commands used.
- `ruff check src tests/test_*.py` → All checks passed
- `mypy src/skynet` → Success, 10 source files
- `nix build .#checks.x86_64-linux.skynet` → exit 0
- `nix flake check --no-build` → all checks passed (pre-existing app-meta / system-rename / deploy-output warnings only)
- offline doctor + disposable missing-evidence status → recorded in the PR
- full staged hook + `git diff --cached --check` → recorded in the PR

No live OPNsense read, config write, credential/pin change, git operation, root, grant, or production
write occurred. Live OPNsense API behavior and firewall write policy unchanged; no replacement offline
collector added; P17 recovery not redesigned.

## Graveyard — tried & abandoned
- Deleting the whole `tests/fixtures/firewall/` including the live fixtures → abandoned: only
  `config.xml` was parser-only; the `*.json` files there are the live opnsense collector's fixtures
  (used by `tests/test_opnsense.py`). Wait — those live JSON fixtures actually live under
  `tests/fixtures/opnsense/`, and `tests/fixtures/firewall/` held only `config.xml`, so the whole
  firewall dir was safe to remove.
- Deleting `test_collection.py::test_offline_mirror_replacement…` outright → abandoned: it is not a
  parser-only test, it exercises the freshness receipt contract; rewrote it to keep that coverage.
- Hand-editing `docs/generated/06-agent-digest.md` (stale P6b-ii "remaining work" line) → abandoned:
  §6 forbids hand-editing generated dirs; the digest refreshes from journal/threads on the nightly.

## Follow-ups / open threads
- `docs/generated/06-agent-digest.md:49` still names the retired offline parser as "remaining
  same-phase work"; it will refresh on the next digest render (not hand-edited).
- SKY-025 §9 P6b-i / P6b-ii dated records still name `collect-firewall.sh` / `firewall.py`; left as
  historical evidence (append-only status log), superseded by the P6c entry above.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
