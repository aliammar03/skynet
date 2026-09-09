---
date: 2026-09-09
time: 11:18:22
kind: session
title: SKY-025 P5 combined independent review
tier_touched: [T1]
grants: []
refs: [SKY-025, "PR #223", "PR #224"]
thread_status: open
---

# 2026-09-09 · session · SKY-025 P5 combined independent review

## What happened

Ali requested `planning/prompts/review.md`, PR #224 and P5a #223. I read the prompt,
directive, map, construction/git/docs conventions and relevant callers/tests. GitHub returned:
#223 merged at `c0e0f53007dee3d49779c4f7fca065fbac13dbd2`;
#224 merged at `e09a8fc220d610cf6c5d60ac5471cdf0d67bcbe3`.
Remote main was the latter. The phase base is `faf961ab3accb9466385da32efa9bb6185c77f3b`;
the log has only those two slices after it. The main checkout had generated/inventory changes.
I created `/tmp/skynet-sky-025-p5-review`, branch `plan/sky-025-p5-review`, at reviewed main.

The invoking thread's selected metadata was `gpt-6-astra`, medium. Installed catalog lists
that combination; `bin/agent review 'Review SKY-025 P5' --dry-run` resolves it.
One Luna Medium scout inspected only PBS source, old shell, tests and consumers without edits.
Its report found missing status validation, DNS-alias SNI fallback regression and mocked TLS
coverage. It could not run bare pytest; the lead used the repository's Nix environment.

## Actions & outcomes

- `git diff faf961a..HEAD` scoped by changed source/caller/test paths showed Docker still in
  `REMAINING`, as well as the new direct Python collector. The retained shell forwards back
  into the isolated CLI and overwrites the same file without updating its marker.
- I created external probes at `/tmp/skynet-p5-review-probes.FIhV6e/test_review.py`.
  `nix develop --no-write-lock-file -c env
  DOCKER_CONFIG=/tmp/skynet-p5-review-probes.FIhV6e/docker-config
  PYTHONPATH=/tmp/skynet-sky-025-p5-review/src:/tmp/skynet-sky-025-p5-review/tests
  pytest -q /tmp/skynet-p5-review-probes.FIhV6e/test_review.py` returned **5 passed**.
  These assertions demonstrate defects, not acceptance:
  1. With synthetic Proxmox/PBS/Docker and a fake remaining reader that rewrites Docker
     `images`, `collect_all` returns 0/success; immediate `collection_status` returns 3.
  2. `docker._lines(json.dumps(dict.fromkeys(required)), required)` accepts a container
     with null ID, Names, Image, State, Status and Labels.
  3. `docker._run` runs a local Python parent which spawns a sleeping child and writes its
     PID into the disposable directory. With timeout 0.3 seconds the collector raises
     CollectionError, but `os.kill(child, 0)` still succeeds. The probe kills that exact
     owned child in its finally block.
  4. Synthetic PBS status `{"used":"400"}` with no total passes `pbs.snapshot`.
  5. All synthetic latest PBS verification states set to `failed` produce `unverified=0`.
     Executing the actual renderer PBS block (lines 280–309) against this disposable JSON
     emits `[!success]` and no failed-state warning.
- The old shell selects SAN/CN when no PBS_SNI is present. Python `_certificate_name`
  instead returns any configured non-IP host before reading the certificate. For a dial
  alias `pbs.internal` and certificate DNS `pbs.example.test`, it returns the alias.
  This changes the packet's preserved fallback and can refuse a previously working TLS read.
- `nix develop --no-write-lock-file -c pytest -q`: **118 passed in 18.67s**.
  While inspecting the suite I discovered the generated runner in
  `test_signal_interrupts_reader_and_reaps_child` substitutes Proxmox/PBS but not Docker.
  I polled the running suite and inspected process metadata; it had already completed before
  a stop was possible. Docker exists at `/run/current-system/sw/bin/docker`; therefore this
  first run cannot be called isolated. It may have contacted the configured Docker endpoint.
  No endpoint log or Docker configuration was read to claim otherwise.
- I then placed a synthetic `docker` executable in the probe directory. It records arguments
  and exits 3. Running only the two signal cases with this executable first on PATH and a
  disposable DOCKER_CONFIG returned **2 passed, 33 deselected in 2.74s**, with exactly:
  `context inspect docker-dmz`, `context inspect docker-dmz`.
  This confirms the missing substitution without contacting Docker. Future execution must
  repair isolation before ordinary suite runs. No production mutation was attempted.
- Ruff returned `All checks passed!`; mypy returned no issues in 8 source files.
  `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` succeeded
  (cached derivation), and `nix flake check --no-write-lock-file --no-build` passed.
  Existing renamed-system/app-meta/unknown-deploy warnings remained.
  The package result does not replace the missing TLS tests; `test_docker.py` also
  unconditionally prepends the source directory despite installed-console mode.
- `bin/skynet doctor --json`: success, Python 3.13.15, package 0.1.0.
  `bin/skynet collect-status --repo /tmp/skynet-p5-review-probes.FIhV6e --json`:
  unavailable, exit 3. No collection was requested by these commands.
- Published planning content only: §5 repair packet and §9 full P5 FIX evidence, map disposition,
  this journal, generated digest/context. Kept accepted progress 4/24, no P6, no gate promotion.
  The existing five documentation suites were not run or counted as passing.
  Full staged hook and cached whitespace check were run before commit.

## Graveyard — tried & abandoned

- The first remote-main API request used `aliammar/skynet` and returned 404; PR metadata
  supplied the actual `aliammar03/skynet` owner, whose API request succeeded.
- A broad model-cache text search included unrelated catalog metadata. Replaced it with jq
  selecting only slug and supported efforts, plus current session model/effort.
- First probe invocation put relative PYTHONPATH before `nix develop`; pytest could not
  import `test_collection`. Re-ran with absolute paths via `nix develop -c env`.
- Did not accept green suite/package results as sufficient: the five counterexamples and
  missing substitutions contradict the packet exits. No implementation repair was made.

## Follow-ups / open threads

- After Ali merges this P5 FIX planning PR, use Terra High:
  `Read planning/prompts/execute.md and execute SKY-025 P5 fix.`
  After fix PR(s) merge, request fresh Astra Medium review of #223, #224 and all fixes.
- Workstation/state/payload recovery and live endpoint parity remain unverified. No live
  PBS/Docker permission is released by the fix packet; no root/grant, activation, timer/service,
  credential/pin change, backup/restore/prune or payload/state action occurred.
