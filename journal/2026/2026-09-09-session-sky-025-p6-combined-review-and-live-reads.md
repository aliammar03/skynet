---
date: 2026-09-09
time: 18:52:45
kind: session
title: SKY-025 P6 combined review and live reads
tier_touched: [T1]
grants: []
refs: [SKY-025, "PR #226", "PR #227", "PR #228"]
thread_status: open
---

# 2026-09-09 · session · SKY-025 P6 combined review and live reads

## What happened

Ali requested the review workflow for all three numbered-P6 slices and a live test, then
explicitly requested Luna workers. GitHub confirmed all three merged into main:
#226 `b7e6f6e8e1dd69f8bbe0f54d91738f9bced4a1b8`,
#227 `ea50741c8a25cac9b72a460c3ef08395403dea41`, and
#228 `9858daf0b4405b14aa93f45f50d71349ea29b1b6`.
The packet baseline was `db09021802f590d79f2ab9f7c2c56064f29c0a4a`; only these three
commits intervene. Main had unrelated generated/inventory edits, including untracked
`inventory/tofu-drift.txt`. I created `/tmp/skynet-sky-025-p6-review` from remote main,
then named its branch `fix/sky-025-p6-review`. Main's changes were preserved.

Two Luna Medium scouts inspected separate OPNsense and DNS/offline-parser surfaces.
Two Luna High builders subsequently owned disjoint module/test pairs. Neither received
credentials or production authority; I retained live reads, integration tests, documentation,
planning and acceptance. The reviewer session identifies as GPT-6; exact selected variant
and effort were not exposed, and the review workflow does not require either.

## Actions & outcomes

- Independently ran `nix develop --no-write-lock-file -c pytest -q` before repairs:
  193 passed in 22.23s. Ruff and mypy passed (11 modules).
- `bin/skynet collect dns --output /tmp/skynet-p6-live.0M8zWC/dns-before.json --json`
  exited 1 with `API request not ok`. A pinned-HTTPS read probe printed only endpoint,
  zone, HTTP/API status and fixed error categories. `zones/list` succeeded, as did
  the three named-zone record reads; the empty root zone failed. Repeating its read
  with `domain=.&zone=.` succeeded. No exclusion of the root zone was accepted.
- `bin/skynet collect opnsense --firewall-output .../firewall-before.json
  --state-output .../opnsense-before.json --json` exited 3 before networking:
  `invalid credential assignments`. An in-memory key-name-only check showed
  `OPN_USER` alongside the supported assignments. No credential value was printed,
  copied or changed. The builder was given the metadata key name, not the file.
- `bin/skynet collect firewall --output .../offline-firewall.json --json` read the
  existing local mirror without a git pull: 41 aliases, 29 rules, 5 reservations,
  collected 2026-09-09T13:51:37Z. Only the parser's count/provenance report was printed.
- The DNS builder normalized only request spelling and validated address/CNAME data.
  `PYTHONPATH=src python3 -m skynet collect dns --output .../dns-after.json --json`
  then succeeded at 2026-09-09T13:54:09Z: 4 zones and 13,355 records.
- Added independent integration checks for initial/final DNS and both OPNsense marker
  failures, refusal of previous success, recovery, and an actual offline parse replacing
  a successfully marked live snapshot. `pytest -q tests/test_collection.py` passed
  49 tests in 16.55s.

## Graveyard — tried & abandoned

- Synthetic tests alone missed both real API/credential incompatibilities. The live root
  request adjustment was verified directly instead of skipping that zone.
- A scout reported a duplicate `protocol` dictionary key; inspection and Ruff did not
  substantiate it. Another claimed missing offline rule fields make jq fail; jq's null
  handling and legacy XML contracts did not support requiring modern live fields for every
  legacy row. No such parser restriction was added.
- Two OPNsense file replacements cannot form one filesystem transaction. The packet
  requires all reads/validation before replacement and paired receipt gating; it does not
  require a new transaction framework. Kept that boundary, corrected the overclaim in
  documentation, and tested refusal after publication/marker failure.
- Nix emitted an ignored evaluation-cache busy warning during concurrent read checks;
  each command's exit and final result were still checked.

## Follow-ups / open threads

- Complete OPNsense repair/live retest, full installed/source checks and review publication.
- No production inventory replacement, timer/service change, activation, root session,
  credential/pin change, zone write or firewall write occurred. The tests used disposable
  outputs; workstation/state/payload recovery remains unverified.

## Final repair validation and disposition

The OPNsense worker repaired credential metadata, certificate SNI precedence, nested response
validation, search totals/configured-rule completeness, form selections and ICMP error reporting.
I inspected its diff and required preservation of alias enabled strings, empty content mappings,
and optional interface flags. A live shape probe showed enabled values true/false/null on
interfaces; rejecting null had failed the intermediate parser. The actual source CLI passed
at 13:59:19Z with 40 aliases, 28 rules, 44 ARP entries and 17 interfaces.

An intermediate package build failed one new ping regression because its transport fixture
still replaced the function being tested. The worker captured/restored the real functions and
kept only the subprocess boundary fake. The final independent command
`nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` passed, followed by
`nix develop --no-write-lock-file -c pytest -q`: 225 passed in 25.62s. Ruff over source and all
Python tests passed; mypy passed all 11 modules. Flake evaluation passed with existing app-meta,
deploy-output and renamed-system warnings. Doctor returned success; disposable collect-status
returned unavailable with exit 3. The five paused documentation suites were not run.

Final packaged commands used `bin/skynet` from the review checkout. DNS succeeded at
2026-09-09T15:45:19Z: 4 zones, 13,355 records. OPNsense succeeded at 15:45:22Z:
40 user aliases, 28 configured rules, 41 ARP entries, 17 interfaces. All output files remain
under `/tmp/skynet-p6-live.0M8zWC`; no raw credentials or config.xml were copied into git.
ARP count changed between observations, as expected for live neighbor state. Mirror counts
are separate historical observations, not a claim of API parity or mirror freshness.

Verdict: P6 ACCEPT with the verified repairs in the combined review PR, effective at Ali's
merge. Accepted progress becomes 6/24. Released only P7a Omada with Terra High; its packet
excludes live Omada access. P7b certs/routes and P7c recon remain same-phase continuations.
No G checkpoint is due. Human merge remains required; no next-phase implementation occurred.

Publication checks: the full staged hook passed, including invariant/secret, rollback,
construction, nightly safety and Python checks (225 passed in 25.57s). Staged diff whitespace
check passed. Remote main remained `9858daf0b4405b14aa93f45f50d71349ea29b1b6` at final fetch.
